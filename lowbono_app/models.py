import datetime
import re
import random
import string
from django.apps import apps
from django.db import models
from django.db.models import Q, Subquery
from django.db.models.signals import m2m_changed
from django.contrib.contenttypes.models import ContentType
from ckeditor.fields import RichTextField
from django.conf import settings
from django.conf import global_settings
from localflavor.us.models import USStateField, STATE_CHOICES
from phonenumber_field.modelfields import PhoneNumberField
from django.utils.translation import gettext_lazy as _
import secrets
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.text import slugify
from datetime import date

from django.contrib.auth.models import AbstractUser, BaseUserManager
from simple_history.models import HistoricalRecords
from html_sanitizer.django import get_sanitizer
from django.db.models.signals import post_save
from django.dispatch import receiver

from django.template import Context, Template
from bs4 import BeautifulSoup

from . import constants
from . import emails
from . import utils
from . import tasks

sanitizer = get_sanitizer()

class UserManager(BaseUserManager):

    def create_user(self, email, password=None):
        """ Create a new user profile """
        if not email:
            raise ValueError("Users must have an Email address")

        user = self.model(email=self.normalize_email(email))
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password):
        """ Create a new superuser profile """
        user = self.create_user(email, password)
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)

        return user

    def signup(self, token, email, password):
        token = get_object_or_404(Token, token=token)
        user = get_object_or_404(User, token=token, email=email)
        user.set_password(password)
        user.save()
        token.delete()

    def overdue_professionals_for_event(self, event_type):
        """ Get professionals who have overdue workflows for a specific event type """

        workflow_name = event_type.template.workflow_type.model_class().__name__.lower()

        return self.filter(
            **{
                f'referral__{workflow_name}__current_task__name': event_type.workflow_state,
                f'referral__{workflow_name}__updated_at__lt': timezone.now() - datetime.timedelta(days=event_type.days_inactive)
            }
        ).distinct()


class User(AbstractUser):
    email = models.EmailField(_("email address"), blank=False, null=False, unique=True)
    username = models.CharField(_("username"), max_length=150, unique=False)

    first_name = models.CharField(_("first name"), max_length=150, blank=False, null=False)
    last_name = models.CharField(_("last name"), max_length=150, blank=False, null=False)
    firm_name = models.CharField(max_length=300)
    phone = PhoneNumberField()
    address = models.TextField()
    photo = models.ImageField(upload_to='headshots')
    bio = RichTextField()
    is_profile_complete = models.BooleanField(default=False, blank=False, null=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.get_full_name() + ' [' + self.email + ']'

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = (self.first_name.replace(' ', '') + self.last_name.replace(' ', '') + "_" + ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(5))).lower()
        self.is_profile_complete = self._is_profile_complete()
        self.email = self.email.lower()
        super().save(*args, **kwargs)

    def _is_profile_complete(self):
        return bool(self.email and self.first_name and self.last_name
                    and self.firm_name and self.phone and self.address
                    and self.photo and self.bio)

    def get_absolute_url(self):
        return reverse('user-detail', kwargs={'id': self.id})

    def get_absolute_update_url(self):
        return reverse('user-update', kwargs={'id': self.id})

    def get_full_name(self):
        return self.first_name + " " + self.last_name

    def get_languages_display(self):
        return [lang.get_language_display() for lang in self.languages.all()]

    def get_languages(self, display=False):
        return list(self.languages.all().values_list('language', flat=True))

    def set_languages(self, languages):
        languages = [Language.objects.get_or_create(language=lang, user=self)[0] for lang in languages]
        self.languages.set(languages)
        return languages

    def is_on_vacation(self):
        _date = date.today()
        if self.vacations.filter(first_day__lte=_date).filter(Q(last_day=None) | Q(last_day__gte=_date)):
            return True
        return False

    def invite(self, profile_type):

        from lowbono_lawyer.models import Lawyer
        from lowbono_mediator.models import Mediator

        # create Lawyer object
        if profile_type in ['lawyer', 'both']:
            lawyer = Lawyer(user=self)
            lawyer.save()

        # create Mediator object
        if profile_type in ['mediator', 'both']:
            mediator = Mediator(user=self)
            mediator.save()

        # create token for signup link
        token = Token(user=self)
        token.save()
        token.send_invite_email()
        return token

    def clean(self):
        self.bio = sanitizer.sanitize(self.bio)


@receiver(post_save, sender=User)
def post_save_user(sender, instance, created, **kwargs):
    if hasattr(instance, 'lawyer_user') and instance.lawyer_user.id:
        instance.lawyer_user.is_profile_complete = instance.lawyer_user._is_profile_complete()
        instance.lawyer_user.save()
    if hasattr(instance, 'mediator_user') and instance.mediator_user.id:
        instance.mediator_user.is_profile_complete = instance.mediator_user._is_profile_complete()
        instance.mediator_user.save()


class ReferralSource(models.Model):
    source = models.CharField(max_length=128)

    def __str__(self):
        return self.source


class PovertyLineRate(models.Model):

    first_household_member_rate = models.IntegerField(blank=False, null=False, default=1)
    additional_household_member_rate = models.IntegerField(blank=False, null=False, default=1)

    def __str__(self):
        return 'poverty line rates - 1st: ' + str(self.first_household_member_rate) + ' additional: ' + str(self.additional_household_member_rate)


class Referral(models.Model):
    professional = models.ForeignKey(User, null=True, on_delete=models.PROTECT, verbose_name=_('Who would you like to have a consultation with?'))

    first_name = models.CharField(_("First Name"), max_length=150, blank=False, null=False)
    last_name = models.CharField(_("Last Name"), max_length=150, blank=False, null=False)
    email = models.EmailField(_("Email"), blank=False, null=False)
    phone = PhoneNumberField(_("Phone"))
    address = models.TextField()
    zipcode = models.CharField(max_length=5, blank=True, null=True, default=None)

    monthly_income = models.IntegerField(blank=True, null=True)
    household_size = models.IntegerField(blank=True, null=True)
    income_status = models.CharField(max_length=16, choices=constants.INCOME_STATUS_CHOICES, blank=True, null=True)
    in_dc = models.BooleanField(default=True, blank=False, null=False)
    allow_llm = models.BooleanField(default=False, blank=False, null=False)
    language = models.CharField(_('Your Language'), max_length=7, choices=global_settings.LANGUAGES, default='en')

    practice_area = models.ForeignKey('PracticeArea', null=True, on_delete=models.PROTECT, verbose_name=_('Can you tell us more about your issue?'))

    issue_description = models.TextField(blank=True, null=True, verbose_name=_('Briefly describe your legal issue'))

    follow_up_consent = models.BooleanField(default=False, verbose_name=_("May we follow up with you about your request (for example, with a request summary and survey)"))
    contact_preference = models.CharField(max_length=1, choices=constants.CONTACT_PREFERENCES_CHOICES, verbose_name=_("If you request a consultation, do you give the lawyer permission to contact you?"))

    deadline_date = models.DateField(blank=True, null=True, default=None, verbose_name=_('when'))
    deadline_reason = models.CharField(max_length=32, blank=True, null=True, verbose_name=_('what'), choices=constants.COURT_APPEARANCE_MATTER)

    referred_by = models.ForeignKey(ReferralSource, null=True, on_delete=models.PROTECT, verbose_name=_('How did you find us?'))

    created_at = models.DateTimeField(auto_now_add=True)

    def get_full_name(self):
        return self.first_name + " " + self.last_name

    def __str__(self):
        return 'Client: ' + self.get_full_name() + ' --> Lawyer: ' + self.professional.get_full_name()


class ReferralNotifications(models.Model):
    """ stores email/notifications sent """

    referral = models.ForeignKey(Referral, on_delete=models.CASCADE)
    template = models.ForeignKey('EmailTemplates', null=True, on_delete=models.PROTECT)
    subject = models.CharField(max_length=512, blank=True, null=True)
    message = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=16, default='None', choices=constants.EMAIL_STATUS)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Referral Notification'
        verbose_name_plural = 'Referral Notifications'

    def __str__(self):
        return f'Notification for Referral: {self.referral}'

    def __repr__(self):
        return f'<{self.__str__}>'


class ReferralNote(models.Model):
    note = models.TextField()
    staff = models.ForeignKey(User, null=True, on_delete=models.PROTECT)
    referral = models.ForeignKey(Referral, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Note by Staff for Referral'
        verbose_name_plural = 'Notes by Staff on Referrals'

    def __str__(self):
        return f'Note for Referral: {self.referral} by Staff: {self.staff.get_full_name()}'

    def __repr__(self):
        return f'<{self.__str__}>'


class ProfileNote(models.Model):
    note = models.TextField()
    admin = models.ForeignKey('User', related_name='admin', null=True, on_delete=models.PROTECT)
    professional = models.ForeignKey('User', related_name='professional', null=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Note by Admin on Professional'
        verbose_name_plural = 'Notes by Admin on Professionals'

    def __str__(self):
        return f'Note for Professional: {self.professional.get_full_name()} by Admin: {self.admin.get_full_name()}'

    def __repr__(self):
        return f'<{self.__str__}>'


class ProfessionalQuerySet(models.QuerySet):
    def practices_in(self, practice_area, profile_type):
        """
        Given a PracticeArea model instance, return all professionals
        that practice in that practice area.

        NOTE: Currently only returns professionals that practice in
        that practice area or in the immediate parent practice area.
        """
        if profile_type == 'lawyer':
            return self.filter(lawyerpracticeareas__approved=True).filter(lawyerpracticeareas__practicearea=practice_area).distinct()
        if profile_type == 'mediator':
            return self.filter(mediatorpracticeareas__approved=True).filter(mediatorpracticeareas__practicearea=practice_area).distinct()
        return self

    def is_on_vacation(self, _date=None):
        """
        Return all professionals on vacation

        pass in a date for testing purposes
        """
        if _date is None:
            _date = date.today()

        return self.filter(user__vacations__first_day__lte=_date).filter(Q(user__vacations__last_day=None) | Q(user__vacations__last_day__gte=_date))

    def is_ready_for_referrals(self):
        """
        Return all professionals that are both enabled and their profiles are complete.
        """
        return self.filter(is_enabled=True, is_profile_complete=True, user__is_profile_complete=True)

    def is_working(self, _date=None):
        """
        Return all professionals not on vacation

        pass in a date for testing purposes
        """
        if _date is None:
            _date = date.today()

        return self.filter(Q(user__vacations=None) | Q(user__vacations__first_day__gt=_date) | Q(user__vacations__last_day__lt=_date))

    def is_user_profile_active(self):
        """
        Return all active users i.e. user profile is active
        """
        return self.filter(user__is_active=True)

    def get_lawyer_matches(self, practice_area):
        """
        Return all available matching lawyer professionals
        """
        return self.is_user_profile_active().is_ready_for_referrals().is_working().practices_in(practice_area, 'lawyer')

    def get_mediator_matches(self, practice_area):
        """
        Return all available matching mediator professionals
        """
        return self.is_user_profile_active().is_ready_for_referrals().is_working().practices_in(practice_area, 'mediator')

    def save(self, *args, **kwargs):
        self.is_profile_complete = self._is_profile_complete()
        super().save(*args, **kwargs)


class Professional(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=False, null=False)
    is_enabled = models.BooleanField(default=False, blank=False, null=False)
    is_profile_complete = models.BooleanField(default=False, blank=False, null=False)

    objects = ProfessionalQuerySet.as_manager()

    class Meta:
        abstract = True

    def __str__(self):
        return f'{self.__class__.__name__} info for {self.user.email}'

    def __repr__(self):
        return f'<{self.__str__}>'

    def _is_profile_complete(self):
        return bool(self.practice_areas.count())


def _update_is_profile_complete(instance, action, reverse, **kwargs):
    """
    Handler for practice_areas m2m signal handler.
    Updates is_profile_complete whenever the m2m changes.
    """
    if reverse:
        raise NotImplementedError(f'reverse m2m changes for Professionals not supported ({instance}, {action}, {reverse})')
    if action.startswith('pre_'):
        return
    instance.is_profile_complete = instance._is_profile_complete()
    instance.save()


class Token(models.Model):
    token = models.CharField(max_length=43, unique=True, blank=False, null=False, primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='token')

    def save(self, *args, **kwargs):
        self.token = secrets.token_urlsafe()
        return super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('signup', kwargs={'token': self.token})

    def send_invite_email(self, host=None):
        host = host or settings.HOST
        url = f'{host}{self.get_absolute_url()}'

        template_vars = {"URL": url}
        subject, text_content, html_content = utils.generateSystemEmailTemplates(system_email_event='invite', template_vars=template_vars)

        emails.send_email(to_email=self.user.email, subject=subject, text_content=text_content, html_content=html_content)


class PracticeAreaCategory(models.Model):
    id = models.CharField(max_length=14, primary_key=True, null=False, blank=False, unique=True)
    title = models.CharField(max_length=256, blank=False, null=False)
    definition = models.TextField(null=False)
    practicearea_category_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True,  related_name="practicearea_category_type", limit_choices_to=Q(app_label__icontains='lowbono') & (Q(app_label__icontains='lawyer') | Q(app_label__icontains='mediator')) & (~Q(model__icontains='referral') & ~Q(model__icontains='practice')))

    class Meta:
        verbose_name_plural = 'Practice Area Categories'

    def __str__(self):
        return f'{self.title[:50]}{"..." if len(self.title) > 50 else ""}'

    def __repr__(self):
        return f'{self.title[:50]}{"..." if len(self.title) > 50 else ""}'

class PracticeArea(models.Model):
    id = models.CharField(max_length=14, primary_key=True, null=False, blank=False, unique=True)
    title = models.CharField(max_length=256, blank=False, null=False)
    definition = models.TextField(null=False)
    append_to_llm_definition = models.TextField(null=True, blank=True)
    alternative_to_llm_definition = models.TextField(null=True, blank=True)
    parent = models.ForeignKey('PracticeAreaCategory', null=True, on_delete=models.PROTECT, related_name='children')
    practicearea_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True,  related_name="practicearea_type", limit_choices_to=Q(app_label__icontains='lowbono') & (Q(app_label__icontains='lawyer') | Q(app_label__icontains='mediator')) & (~Q(model__icontains='referral') & ~Q(model__icontains='practice')))

    class Meta:
        verbose_name_plural = 'PracticeAreas'

    def __str__(self):
        return f'{self.title[:50]}{"..." if len(self.title) > 50 else ""}'

    def __repr__(self):
        return f'{self.title[:50]}{"..." if len(self.title) > 50 else ""}'

class Language(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='languages')
    language = models.CharField(max_length=7, choices=constants.NON_EN_LANGUAGES)
    bio = RichTextField(blank=True, null=False, default='')

    class meta:
        unique_together = ('user', 'language')

    def clean(self):
        self.bio = sanitizer.sanitize(self.bio)


class BarAdmission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bar_admissions")
    state = USStateField()
    admission_date = models.DateField()
    bar_number = models.CharField(max_length=32, blank=False, null=False)

    class meta:
        unique_together = ('user', 'state')

    def get_bar_admissions_display(self):
        # TODO: return full name of state shortcode
        return (self.state, self.admission_date)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.user.is_profile_complete = self.user._is_profile_complete()
        self.user.save()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.user.is_profile_complete = self.user._is_profile_complete()
        self.user.save()


class Vacation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vacations')
    first_day = models.DateField()
    last_day = models.DateField(null=True, blank=True)


class SystemEmailEvents(models.Model):
    template = models.OneToOneField("SystemEmailTemplates", on_delete=models.CASCADE, blank=True, null=True)
    event_name = models.CharField(max_length=128, default='')

    class Meta:
        verbose_name = 'System EmailEvent'
        verbose_name_plural = 'System EmailEvents'

    def __str__(self):
        return f'System Email Event: {self.event_name}'


class SystemEmailTemplates(models.Model):
    description = models.CharField(max_length=256, blank=True, default='', null=True)
    subject = models.CharField(max_length=512, blank=False, null=False)
    body = RichTextField(blank=False, null=False)
    active = models.BooleanField(default=True, blank=False, null=False)

    class Meta:
        verbose_name = 'System Email Template'
        verbose_name_plural = 'System Email Templates'

    def __str__(self):
        return f'System Email Template: {self.description}'


class EmailEventEnterState(models.Model):
    template = models.OneToOneField("EmailTemplates", on_delete=models.CASCADE, blank=True, null=True)
    workflow_state = models.CharField(max_length=128, default='')
    days_after = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'EmailEvent Enter State'
        verbose_name_plural = 'EmailEvents Enter State'

    def save(self, *args, **kwargs):
        if self.template.event_type == self.__class__.__name__.lower():
            super().save(*args, **kwargs)

    def __str__(self):
        return f'at state: {self.template.workflow_type.model_class().pretty_nodes[self.workflow_state] if self.template.workflow_type else self.workflow_state} {", send after " + str(self.days_after) + " days" if self.days_after else ""}'


class EmailEventInactiveFor(models.Model):
    template = models.OneToOneField("EmailTemplates", on_delete=models.CASCADE, blank=True, null=True)
    workflow_state = models.CharField(max_length=128, default='')
    days_inactive = models.IntegerField(default=0)

    def send_overdue_notification_to_professionals(self):
        for professional in User.objects.overdue_professionals_for_event(self):
            self.template.send_bulk_email(professional.id)

    class Meta:
        verbose_name = 'EmailEvent InactiveFor'
        verbose_name_plural = 'EmailEvents InactiveFor'

    def save(self, *args, **kwargs):
        if self.template.event_type == self.__class__.__name__.lower():
            super().save(*args, **kwargs)

    def __str__(self):
        return f'at state: {self.template.workflow_type.model_class().pretty_nodes[self.workflow_state] if self.template.workflow_type else self.workflow_state} {", send every " + str(self.days_inactive) + " days" if self.days_inactive else ""}'


class EmailEventDeadline(models.Model):
    template = models.OneToOneField("EmailTemplates", on_delete=models.CASCADE, blank=True, null=True)
    workflow_state = models.CharField(max_length=128, default='')
    days = models.IntegerField(default=0)
    before_or_after_deadline = models.CharField(max_length=4, default='-', choices=[('+', 'After Deadline'), ('-', 'Before Deadline')])

    class Meta:
        verbose_name = 'EmailEvent Deadline'
        verbose_name_plural = 'EmailEvents Deadline'


    def save(self, *args, **kwargs):
        if self.template.event_type == self.__class__.__name__.lower():
            super().save(*args, **kwargs)

    pretty_before_or_after = {'-': 'before', '+': 'after'}

    def __str__(self):
        return f'at state: {self.template.workflow_type.model_class().pretty_nodes[self.workflow_state] if self.template.workflow_type else self.workflow_state}, {self.days} days {self.pretty_before_or_after[self.before_or_after_deadline]} deadline'


class EmailTemplates(models.Model):
    description = models.CharField(max_length=256, blank=True, default='', null=True)
    subject = models.CharField(max_length=512, blank=False, null=False)
    body = RichTextField(blank=False, null=False)

    workflow_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True,  related_name="workflow_type", limit_choices_to=Q(app_label__icontains='lowbono') & Q(model__icontains='workflow') & ~Q(model__icontains='historical') & ~Q(model__icontains='referralworkflowstate'))
    recipient = models.CharField(max_length=128, choices=constants.EMAIL_TO_RECIPIENT_CHOICES, default='')

    event_type = models.CharField(max_length=128, choices=[(None, '[select event type]'), ('emailevententerstate', 'when a workflow enters state'), ('emaileventinactivefor', 'when a workflow has been inactive'), ('emaileventdeadline', 'when there is a deadline')], null=True, blank=True)

    active = models.BooleanField(default=True, blank=False, null=False)


    def clean(self):
        if not self.workflow_type:
            raise ValidationError(f"Oops, please add a valid workflow type")
        if not self.event_type:
            raise ValidationError(f"Oops, please add a valid event type")

    def send_bulk_email(self, professional_id):
        """
            For a 'professional', get list of 'overdue workflows' for that 'event_type'
            Sends a single email with all the overdue referrals list
            Updates Workflow and ReferralNotifications model for each overdue referral
        """

        professional = User.objects.get(id=professional_id)
        event_type = getattr(self, self.event_type)
        overdue_workflows = self.workflow_type.model_class().objects.get_overdue_workflows_for_professional(event_type=event_type, professional=professional)

        overdue_referrals = []
        for workflow in overdue_workflows:
            overdue_referrals.append({'CLIENT_NAME': workflow.referral.get_full_name(),
                                      'LAST_UPDATED': workflow.human_last_updated_at_pretty_date(),
                                      'REFERRAL_LINK': f'{settings.HOST}{reverse("referral-detail", args=[workflow.referral.id])}',
                                     })

        template_vars = {'PROFESSIONAL_NAME': professional.get_full_name(),
                         'PROFESSIONAL_EMAIL': professional.email,
                         'MAGIC_LINK_TO_ALL_PENDING_REFERRALS': self.workflow_type.model_class().get_bulk_update_dashboard_link(professional.id, event_type.workflow_state),
                         'OVERDUE_MATTERS_LIST': overdue_referrals,}

        to_email = template_vars[self.recipient]
        subject = Template(self.subject).render(Context(template_vars))
        html_content = Template(self.body).render(Context(template_vars))
        text_content = BeautifulSoup(html_content, features="html.parser").get_text()

        tasks.dispatch_email_via_api.delay(to_email=to_email, subject=subject, text_content=text_content, html_content=html_content)

        for workflow in overdue_workflows:
            notification = ReferralNotifications.objects.create(referral_id=workflow.referral.id, template=self, subject=subject, message=text_content)
            workflow.notification = notification
            workflow.is_human_activity = False
            workflow.save()

    def send_email(self, referral, workflow=None, task_id=None):
        """
            generates html/text template using given template variables
            adds a 'ReferralNotifications' entry
            schedules a celery task to send actual email using API

            'worflow' flag is used to make an update in Joeflow's model if email is triggered due to workflow state
        """

        template_vars = {'PROFESSIONAL_NAME': referral.professional.get_full_name(),
                         'PROFESSIONAL_PHONE_NUMBER': referral.professional.phone.as_national if referral.professional.phone else '',
                         'PROFESSIONAL_EMAIL': referral.professional.email,
                         'DATE_OF_REFERRAL': referral.created_at.date(),
                         'CLIENT_NAME': referral.get_full_name(),
                         'CLIENT_PHONE_NUMBER': referral.phone.as_national if referral.phone else '',
                         'CLIENT_EMAIL': referral.email,
                         'MATTER_DEADLINE': referral.deadline_date,
                         'LINK_TO_REFERRAL': f'{settings.HOST}{reverse("referral-detail", args=[referral.id])}'}

        to_email = template_vars[self.recipient]
        subject = Template(self.subject).render(Context(template_vars))
        html_content = Template(self.body).render(Context(template_vars))
        text_content = BeautifulSoup(html_content, features="html.parser").get_text()

        notification = ReferralNotifications.objects.create(referral_id=referral.id, template=self, subject=subject, message=text_content)

        tasks.dispatch_email_via_api.delay(to_email=to_email, subject=subject, text_content=text_content, html_content=html_content,
                                           referral_notification_id=notification.id, task_id=task_id)

        if workflow:
            workflow.notification = notification
            workflow.is_human_activity = False
            workflow.save()


    class Meta:
        verbose_name = 'Email Template'
        verbose_name_plural = 'Email Templates'

    def __str__(self):
        return f'Email Template: {self.description}'


class EmailAPILogs(models.Model):
    """ logs in failed email sending attempts due to API failure"""

    to_email = models.CharField(max_length=256, blank=False, null=False)
    api_logs = models.TextField(null=True, blank=True)
    html_content = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Email API Log'
        verbose_name_plural = 'Email API Logs'

    def __str__(self):
        return f'Email API Logs: {self.to_email}'


class CeleryETATasks(models.Model):
    """ task with longer ETAs scheduled to be delivered later on """

    func = models.CharField(max_length=256, blank=False, null=False)
    args = models.JSONField(null=True)
    eta = models.DateTimeField(auto_now_add=False, blank=True, null=True)
    status = models.CharField(max_length=64, blank=True, null=True, choices=[('SCHEDULED', 'Scheduled'), ('DELIVERED', 'Delivered'), ('FAILED', 'Failed'), ('CANCELLED', 'Cancelled'), ], default='SCHEDULED')
    error_log = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Celery ETA Task'
        verbose_name_plural = 'Celery ETA Tasks'

    def __str__(self):
        return f'Celery ETA Task: {self.func} at {self.eta}'


class LLMLogs(models.Model):
    """ stores LLM logs """

    user_query = models.TextField(null=True, blank=True)
    user_prompt = models.TextField(null=True, blank=True)
    instruction_prompt = models.TextField(null=True, blank=True)
    practice_area_matched = models.ForeignKey(PracticeArea, on_delete=models.SET_NULL, null=True)
    llm_result = models.TextField(null=True, blank=True)
    audit_trail = models.TextField(null=True, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'LLM Logs'
        verbose_name_plural = 'LLM Logs'

    def append_to_audit_trail(self, text):
        self.audit_trail += "\n\n" + str(text)
        self.save()


class NewsArticles(models.Model):
    title = models.CharField(max_length=512)
    slug = models.CharField(max_length=512, blank=True, default='', null=True)
    content = RichTextField(config_name='admin_toolbar')
    photo = models.ImageField(upload_to='news_images', blank=True, null=True)
    status = models.CharField(max_length=10, choices=[('draft', 'Draft'), ('published', 'Published')], default='draft',)
    author = models.CharField(max_length=64, default='LowBono Team')
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        original_slug = self.slug
        if not self.pk:
            counter = 1
            while NewsArticles.objects.filter(slug=self.slug).exists():
                self.slug = f'{original_slug}-{counter}'
                counter += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'News Article'
        verbose_name_plural = 'News Articles'
