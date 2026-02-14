import datetime

from django.apps import apps
from django.core.mail import send_mail
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.functional import lazy
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic.edit import FormMixin, ModelFormMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, F, Sum, Max, Subquery, OuterRef
from django.db import models

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, HTML, Submit, Field
from crispy_forms.bootstrap import PrependedText

from joeflow.models import Workflow, Task
from joeflow import tasks

from simple_history.models import HistoricalRecords

from django.http import HttpResponseRedirect
from django.db import transaction
from django.db import models
from lowbono_app.models import Referral, ReferralNotifications, EmailEventEnterState, EmailEventDeadline, EmailEventInactiveFor, CeleryETATasks
from lowbono_app.constants import ATTORNEY_PROVIDED_RATES_BEAUTIFY
from lowbono_app.tasks import emailtemplates_delayed_send_email


class ReferralUpdateViewBase(UserPassesTestMixin, tasks.UpdateView):
    """
        Custom update form that overrides joeflow's default form to help:
            - show empty hours/notes field on each successive update
            - record human_activity or not
    """

    fields = ["hours_worked", "notes", "is_income_eligible", "ineligible_reason"]

    def handle_no_permission(self):
        messages.error(self.request, 'Oops! You do not have permission to access this page')
        return redirect('dashboard')

    def test_func(self, *args, **kwargs):
        if self.request.user.is_staff: return True
        _obj = super(ReferralUpdateViewBase, self).get_object(*args, **kwargs)
        return self.request.user.id == _obj.referral.professional.id

    def get_form_kwargs(self):
        """
        We don't want hours worked and notes to carry over from the last update,
        so we remove them here.
        """
        kwargs = super().get_form_kwargs()
        if hasattr(self, "object"):
            kwargs["instance"].hours_worked = 0
            kwargs["instance"].notes = ''
        return kwargs

    def next_task(self, user_node_choice):
        task = self.get_task()
        task.workflow = self.model._base_manager.get(pk=self.object.pk)
        task.finish(self.request.user)
        next_node = task.workflow.get_node(user_node_choice)
        task.start_next_tasks([next_node]) # start just one task

    @transaction.atomic
    def form_valid(self, form):
        """
        Set is_human_activity to differentiate from a computer event like a
        reminder email.
        """

        is_income_eligible = self.object.referral.income_status in ['low', 'moderate']
        has_engaged = form.cleaned_data.get("user_node_choice") in ['waiting_for_post_engagement_update', 'engagement_completed']

        # validate if ineligbile reason is provided when required
        if (is_income_eligible and has_engaged) and (not form.cleaned_data.get("is_income_eligible") and not form.cleaned_data.get("ineligible_reason")):
            form.add_error('ineligible_reason', 'Please provide a reason')
            return self.form_invalid(form)

        form.instance.is_human_activity = True

        self.next_task(form.cleaned_data.get("user_node_choice"))  # execute tasks
        form.save(self)

        return HttpResponseRedirect(self.get_success_url())
    
    def get_form(self):
        form = super().get_form()

        form.fields['user_node_choice'] = forms.ChoiceField(choices=self.object.dynamic_form_node_choices())
        form.fields['user_node_choice'].label = "Report Status"

        form.fields['hours_worked'].required = False
        form.fields['is_income_eligible'].required = False

        total_reported_hours = self.object.count_total_reported_hours()
        if total_reported_hours > 0:
            last_updated = self.object.human_last_updated_at().strftime("%B %d %Y")
            form.fields['hours_worked'].label = f"Hours worked since last update on { last_updated }"
            form.fields['hours_worked'].help_text = f"Cumulative recorded hours: { total_reported_hours }"

        form.fields['is_income_eligible'].label = f"Did you provide affordable rates to { self.object.referral.get_full_name() }?"
        form.fields['is_income_eligible'].widget = forms.RadioSelect(choices=ATTORNEY_PROVIDED_RATES_BEAUTIFY.items())

        # customize ineligible_reason field's label and help text
        if self.object.referral.income_status:
            form.fields['ineligible_reason'].label = mark_safe(f"Reason why you provided standard rates?<br><small>Client reported they are eligible for affordable rates:<br> Annual income of ${ self.object.referral.monthly_income * 12 } for { self.object.referral.household_size } people</small>")

        form.helper = FormHelper()
        form.helper.layout = Layout(
            'user_node_choice',
            'hours_worked',
            'notes',
            Row(
                Column('is_income_eligible'),
                Column('ineligible_reason'),
            ),
        )
        form.helper.add_input(Submit('submit', 'Update'))

        return form

    def get_success_url(self):
        return reverse('referral-detail', args=[self.object.referral.id])


class CustomJoeflowStart(tasks.Start):
    """ adds initial task to workflow current_task """

    def __call__(self, **kwargs):
        workflow = self.workflow_cls.objects.create(**kwargs)
        task = workflow.task_set.create(name=self.name, type=tasks.MACHINE, workflow=workflow)
        task.finish()
        task.start_next_tasks()

        if workflow.task_set.count():
            workflow.current_task = workflow.task_set.latest()
            workflow.save()

        return workflow


@receiver(post_save, sender=Task)
def post_save_joeflow_task(sender, instance, created, **kwargs):
    if created:

        if instance.workflow.task_set.filter(name=instance.name).count() == 1:
            # transition: entered a new state 1st time

            # EmailEventEnterState emails
            enterstate_events = EmailEventEnterState.objects.filter(template__workflow_type=ContentType.objects.get_for_model(instance.workflow.__class__), workflow_state=instance.name)

            for event in enterstate_events.filter(days_after=0):
                event.template.send_email(instance.workflow.referral, task_id=instance.id) # trigger now

            for event in enterstate_events.filter(days_after__gt=0):
                eta = (datetime.datetime.now() + datetime.timedelta(days=int(event.days_after))).replace(hour=10, minute=0, second=0, microsecond=0)
                CeleryETATasks.objects.create(func='emailtemplates_delayed_send_email', args={"workflow_id": instance.workflow.id, "template_id": event.template.id, "task_id": instance.id}, eta=eta) # to be trigger in future

            # EmailEventDeadline emails
            if instance.workflow.referral.deadline_date:
                for event in EmailEventDeadline.objects.filter(template__workflow_type=ContentType.objects.get_for_model(instance.workflow.__class__), workflow_state=instance.name):
                    calculate_deadline = lambda x, y, op: x + y if op == "+" else x - y
                    eta_date = calculate_deadline(instance.workflow.referral.deadline_date, datetime.timedelta(days=int(event.days)), event.before_or_after_deadline) #.replace(hour=10, minute=0, second=0, microsecond=0)

                    if eta_date <= datetime.date.today():
                        event.template.send_email(instance.workflow.referral, task_id=instance.id) # trigger now
                    else:
                        eta = datetime.datetime(eta_date.year, eta_date.month, eta_date.day).replace(hour=10, minute=0, second=0, microsecond=0)
                        CeleryETATasks.objects.create(func='emailtemplates_delayed_send_email', args={"workflow_id": instance.workflow.id, "template_id": event.template.id, "task_id": instance.id}, eta=eta) # to be trigger in future

        last_task = instance.workflow.task_set.exclude(id__in=[instance.id]).order_by("-id").first()
        if last_task:
            if last_task.name != instance.name:
                # transition: enters a new state comparing to old state
                pass

            if last_task.name == instance.name:
                # transition: resets at same state comparing to old state
                pass


class ReferralWorkflowStateBaseManager(models.Manager):

    def get_overdue_professionals(self, event_type):
        """
            Check if any professional has any overdue notifications for a particular event_type
            Returns all workflows that are overdue for human update, sorted by professionals
            eg: for 'waiting_for_pre_consult' event,
                get list of workflows which are overdue, and prepare list of professionals
                for each professional, get list of human overdue workflows list
                returns a dictionary {professional: [overdue workflows list], ...}
        """

        professional_ids = self.filter(current_task__name=event_type.workflow_state,
                                       updated_at__lt=timezone.now() - datetime.timedelta(days=event_type.days_inactive)) \
                                      .values_list('referral__professional', flat=True).distinct()

        return professional_ids

    def get_overdue_workflows_for_professional(self, event_type, professional):
        """
            Get human update overdue workflows for a professional that are waiting on a particular event_type
            eg: for 'waiting_for_pre_consult' event, and a particular professional
                get list of all workflows which are overdue for a human update
                returns list of all overdue workflows
        """

        # subquery to filter across a workflow instance's history model objects
        human_last_update = self.model.history.field.model.objects.filter(id=OuterRef('pk'), is_human_activity=True) \
                                                                  .order_by('-updated_at').values('updated_at')[:1]

        # filter through task_name, professional as well as value of human_last_update subquery
        overdue_workflows = self.filter(current_task__name=event_type.workflow_state, referral__professional=professional) \
                                .annotate(human_last_update=Subquery(human_last_update)) \
                                .filter(Q(human_last_update__isnull=True) |
                                        Q(human_last_update__lt=timezone.now() - datetime.timedelta(days=event_type.days_inactive)))
        return overdue_workflows

    def get_overdue_referrals_for_professional(self, event_type, professional):
        """
            Get workflows for a professional that are waiting on a particular event_type
            Converts overdue workflows into referral objects
            returns list of overdue referrals
        """

        overdue_workflows = self.get_overdue_workflows_for_professional(event_type, professional)
        overdue_referrals = [_workflow.referral for _workflow in overdue_workflows]

        return overdue_referrals


class ReferralWorkflowStateBase(models.Model):

    pretty_nodes = {} # joeflow nodes
    edges = [] # joeflow edges

    referral = models.OneToOneField(Referral, on_delete=models.CASCADE)

    current_task = models.ForeignKey(apps.get_model('joeflow', 'Task'), on_delete=models.SET_NULL, null=True, blank=True)
    notification = models.ForeignKey(ReferralNotifications, on_delete=models.CASCADE, null=True, blank=True)
    is_human_activity = models.BooleanField(default=True, blank=False, null=False)
    is_overdue = models.BooleanField(default=False, blank=False, null=False)

    hours_worked = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    is_income_eligible = models.BooleanField(blank=False, null=False, default=True)
    ineligible_reason = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, auto_now_add=False)

    logs = HistoricalRecords(related_name='history', inherit=True)

    objects = ReferralWorkflowStateBaseManager()

    class Meta:
        abstract = True

    def get_current_human_node_name(self):
        """
            provides name of latest scheduled 'human' task
            helps indentify where our joeflow transition is currently
        """

        _exists = self.task_set.scheduled().filter(type='human').first() 
        if _exists:
            return _exists.name
        return None

    def workflow_completed(self):
        """
            if latest task.name matches non-first items of edges_tuples i.e. 'engagement_completed', 'closed_without_consult'
        """

        end_edges = {edge[1] for edge in self.get_edges_tuple()} - {edge[0] for edge in self.get_edges_tuple()}
        return self.task_set.latest().name in end_edges

    def get_current_node_name(self):
        """
            provides name of latest task
            helps indentify where our joeflow transition is currently
        """

        return self.task_set.latest().name

    def get_current_node_pretty_name(self):
        """
            provides name of latest task
            helps indentify where our joeflow transition is currently
        """

        return self.pretty_nodes[self.get_current_node_name()]

    def get_pretty_name_for_task(self, task_name):
        """
            returns pretty version of task's name if available, else just return the task_name
        """

        return self.pretty_nodes[task_name] if task_name in self.pretty_nodes.keys() else task_name

    def get_current_task_pretty_name(self):
        """
            return pretty version of workflow's current_task
        """

        return self.get_pretty_name_for_task(self.current_task.name)

    def workflow_task_update_url(self):
        """
            if a scheduled human task is available, joeflow provides an automated URL to update form.
        """

        if self.get_current_human_node_name():
            return self.task_set.scheduled().filter(type='human').first().get_absolute_url()
        return ''

    def dynamic_form_node_choices(self):
        """
            dynamically provide status choices based on current human node
        """

        next_nodes = [e1 for e0, e1 in self.get_edges_tuple() if e0 == self.get_current_human_node_name()]
        return [(key, self.pretty_nodes[key]) for key in next_nodes]

    def count_total_reported_hours(self):
        return self.history.aggregate(Sum('hours_worked'))['hours_worked__sum']

    def get_engagement_reports_for_professionals(self):
        """
            to be shown to professionals on their referral page
                - includes if human activity
                - excludes empty 'hours worked' and 'notes' updates
        """

        return self.history.exclude(is_human_activity=False).exclude(Q(hours_worked=0) & Q(notes=None)).all()
    
    def get_notifications_for_professionals(self):
        """
            to be shown to professionals on their referral page
                - excludes human activity updates
        """

        return self.history.exclude(is_human_activity=True).order_by('-updated_at').all()

    def get_engagement_reports_for_staff(self):
        """
            to be shown to admin on referral page
                - includes if human activity
        """

        return self.history.exclude(is_human_activity=False).exclude(current_task__isnull=True).order_by('-updated_at').all()
    
    def get_all_engagement_reports(self):
        """
            to be shown to admin/staff on referral page, includes everything
        """

        return self.history.order_by('-updated_at').all()

    def human_last_updated_at(self):
        """
            to calculate when was last update received from human update, as joeflow/tasks keep updating during notifications
            returns None if no human updates received
        """

        human_activities = self.history.exclude(is_human_activity=False)
        if human_activities:
            return human_activities.latest().updated_at
        return None

    def human_last_updated_at_pretty_date(self):
        """
            Convert datetime object to a human-readable relative time string.
        """

        date_obj = self.human_last_updated_at()

        if date_obj is None:
            return 'Never Updated'

        time_diff = timezone.now() - date_obj
        if time_diff > datetime.timedelta(days=30):
            return date_obj.strftime("%b %d, %Y")
        return "Recently Updated" if time_diff.days < 3 else f"{time_diff.days} days ago"

    def get_edges_tuple(self):
        """
            retrieve list of edges with names instead of generator functions
        """

        return [(e0.name, e1.name) for (e0, e1) in self.edges]

    def is_referral_ongoing(self):
        """
            checks if current node attribute is of type ReferralUpdateViewBase, if true, its a human task and referral is ongoing
        """

        return isinstance(getattr(self, self.get_current_node_name()), ReferralUpdateViewBase)
