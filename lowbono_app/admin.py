import datetime
import nested_admin
from django import forms
from django.contrib import admin
from django.utils.html import format_html
from django.contrib.auth.admin import UserAdmin as UserAdminBase
from django.utils.translation import gettext, gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.db.models import Case, When
from django.core.exceptions import ValidationError
from django.db.models import Q

from lowbono_app.models import User, BarAdmission, Language, Referral, ReferralSource, ProfileNote, SystemEmailTemplates, EmailTemplates, EmailAPILogs, CeleryETATasks, ReferralNotifications, PracticeAreaCategory, PracticeArea, ReferralNote, PovertyLineRate, EmailEventInactiveFor, EmailEventEnterState, EmailEventDeadline, SystemEmailEvents, NewsArticles
from lowbono_lawyer.models import Lawyer, LawyerPracticeAreas, LawyerReferral, LawyerLLMLogs
from lowbono_mediator.models import Mediator, MediatorPracticeAreas, MediatorReferral
from lowbono_lawyer.workflows import ReferralLawyerWorkflowState, HistoricalReferralLawyerWorkflowState
from lowbono_mediator.workflows import ReferralMediatorWorkflowState, HistoricalReferralMediatorWorkflowState


class ReferralInline(nested_admin.NestedTabularInline):
    model = Referral
    extra = 0
    max_num = 0
    show_change_link = True

    readonly_fields = (
        'first_name',
        'last_name',
        'email',
        'phone',
        'address',
        'practice_area',
        'referral_type',
        'referral_status',
        'is_overdue',
    )

    list_filter = ('first_name', 'last_name', 'referral_type')

    def referral_type(self, obj):
        if hasattr(obj, 'referrallawyerworkflowstate'):
            return "LAWYER"
        if hasattr(obj, 'referralmediatorworkflowstate'):
            return "MEDIATOR"
        return 'Workflow Not Started'
    referral_type.short_description = 'Referral Type'

    def referral_status(self, obj):
        if hasattr(obj, 'referrallawyerworkflowstate'):
            return obj.referrallawyerworkflowstate.get_current_task_pretty_name()
        if hasattr(obj, 'referralmediatorworkflowstate'):
            return obj.referralmediatorworkflowstate.get_current_task_pretty_name()
        return 'Workflow Not Started'
    referral_status.short_description = 'Referral Status'

    def is_overdue(self, obj):
        if hasattr(obj, 'referrallawyerworkflowstate'):
            if obj.referrallawyerworkflowstate.is_overdue:
                return "Yes"
        if hasattr(obj, 'referralmediatorworkflowstate'):
            if obj.referralmediatorworkflowstate.is_overdue:
                return "Yes"
        return "No"
    is_overdue.short_description = 'Is Matter Overdue?'

    def practice_area(self, obj):
        pa = PracticeArea.objects.filter(id=obj.practice_area).first()
        return f'{pa.title} ({pa.parent.title})'
    practice_area.short_description = 'Practice Area'

    fieldsets = ((None, {
        'fields': (
            ('first_name', 'last_name',),
            ('email', 'phone',),
            'address',
            ('practice_area', 'referral_status', 'referral_type', 'is_overdue'),
        ),
    }),)


class BarAdmissionInline(nested_admin.NestedTabularInline):
    model = BarAdmission
    extra = 0


class LawyerPracticeAreasCustomForm(forms.ModelForm):
    class Meta:
        model = LawyerPracticeAreas
        fields = ('practicearea', 'approved')

    def __init__(self, *args, **kwargs):
        super(LawyerPracticeAreasCustomForm, self).__init__(*args, **kwargs)

        self.fields['practicearea'] = forms.ModelChoiceField(queryset=PracticeArea.objects.all())

        pa_choices = []
        for pa in PracticeAreaCategory.objects.filter(practicearea_category_type=ContentType.objects.get_for_model(Lawyer)).extra(select={'pid': 'CAST(id AS INTEGER)'}).order_by('pid'):
            items = []
            for ch in pa.children.all().extra(select={'cid': 'CAST(id AS INTEGER)'}).order_by('cid'):
                items.append((ch.id, ch.title))
            pa_choices.append((pa.title, tuple(items)))

        self.fields['practicearea'].choices = pa_choices


class LawyerPracticeAreasInline(nested_admin.NestedTabularInline):
    model = LawyerPracticeAreas
    extra = 0
    form = LawyerPracticeAreasCustomForm


class LawyerInline(nested_admin.NestedStackedInline):
    model = Lawyer
    inlines = (LawyerPracticeAreasInline,)
    can_delete = False
    extra = 0
    max_num = 0
    readonly_fields = ('is_profile_complete',)


class MediatorPracticeAreasCustomForm(forms.ModelForm):
    class Meta:
        model = MediatorPracticeAreas
        fields = ('practicearea', 'approved')

    def __init__(self, *args, **kwargs):
        super(MediatorPracticeAreasCustomForm, self).__init__(*args, **kwargs)

        self.fields['practicearea'] = forms.ModelChoiceField(queryset=PracticeArea.objects.all())

        pa_choices = []
        for pa in PracticeAreaCategory.objects.filter(practicearea_category_type=ContentType.objects.get_for_model(Mediator)).extra(select={'pid': 'CAST(id AS INTEGER)'}).order_by('pid'):
            items = []
            for ch in pa.children.all().extra(select={'cid': 'CAST(id AS INTEGER)'}).order_by('cid'):
                items.append((ch.id, ch.title))
            pa_choices.append((pa.title, tuple(items)))

        self.fields['practicearea'].choices = pa_choices


class MediatorPracticeAreasInline(nested_admin.NestedTabularInline):
    model = MediatorPracticeAreas
    extra = 0
    form = MediatorPracticeAreasCustomForm


class MediatorInline(nested_admin.NestedStackedInline):
    model = Mediator
    inlines = (MediatorPracticeAreasInline, )
    can_delete = False
    extra = 0
    max_num = 0
    readonly_fields = ('is_profile_complete',)


class LanguageInline(nested_admin.NestedTabularInline):
    model = Language
    extra = 0


class ProfileNoteInlineAdminForm(forms.ModelForm):
    class Meta:
        model = ProfileNote
        fields = ('note', 'admin')

    def __init__(self, *args, **kwargs):
        super(ProfileNoteInlineAdminForm, self).__init__(*args, **kwargs)
        self.fields['admin'] = forms.ModelChoiceField(queryset=User.objects.filter(is_staff=True).all())


class ProfileNoteInlineList(nested_admin.NestedTabularInline):
    model = ProfileNote
    show_change_link = True
    fk_name = "professional"
    readonly_fields = ("note", "admin",)
    # list_display = ("note", "admin", "created_at", )
    extra = 0
    def has_add_permission(self, request, obj=None):
        return False


class ProfileNoteInlineAdd(nested_admin.NestedTabularInline):
    model = ProfileNote
    form = ProfileNoteInlineAdminForm
    fk_name = "professional"
    fields = ("note", "admin",)
    extra = 0
    def has_change_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return False


class UserAdminForm(forms.ModelForm):
    class Meta:
        model = User
        exclude = ()

    def clean(self):
        if self.cleaned_data.get('is_staff') != self.cleaned_data.get('groups').filter(name='Staff').exists():
            raise ValidationError("In Permissions, you need to either select or unselect both the 'Staff Status' and 'Staff' group fields. If unselecting groups value, please hold Cmd/Ctrl key.")


@admin.register(User)
class UserAdmin(nested_admin.NestedModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'correspondence', 'firm_name', 'is_on_vacation', 'lawyer_profile_complete', 'mediator_profile_complete')

    list_filter = ('first_name', 'last_name', 'firm_name', 'is_profile_complete')

    search_fields = ('first_name', 'last_name',)

    inlines = (LanguageInline, LawyerInline, MediatorInline, BarAdmissionInline, ReferralInline, ProfileNoteInlineList, ProfileNoteInlineAdd)
    fieldsets = (
        (None, {'fields': ('username', 'password', 'email')}),
        (_('Public Profile'), {
            'fields': (
                ('first_name', 'last_name',),
                ('firm_name', 'phone',),
                'address',
                'photo',
                'bio',
            )
        }),
        (_('Permissions'), {
            'classes': ('collapse',),
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {
            'classes': ('collapse',),
            'fields': ('last_login', 'date_joined')
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2'),
        }),
    )

    form = UserAdminForm

    def correspondence(self, object):
        return format_html(f"<a href='https://groups.google.com/a/lowbono.org/g/support/search?q={object.email}'>View</a>")

    def lawyer_profile_complete(self, object):
        lawyer = object.lawyer_user
        if lawyer:
            return lawyer.is_profile_complete
        else:
            return None

    def is_on_vacation(self, object):
        return "Yes" if object.is_on_vacation() else "No"

    def mediator_profile_complete(self, object):
        mediator = object.mediator_user
        if mediator:
            return mediator.is_profile_complete
        else:
            return None

    lawyer_profile_complete.admin_order_field = 'lawyer__is_profile_complete'
    mediator_profile_complete.admin_order_field = 'mediator__is_profile_complete'


class ReferralNoteAdminForm(forms.ModelForm):
    class Meta:
        model = ReferralNote
        fields = ('note', 'referral', 'staff')

    def __init__(self, *args, **kwargs):
        super(ReferralNoteAdminForm, self).__init__(*args, **kwargs)
        self.fields['staff'] = forms.ModelChoiceField(queryset=User.objects.filter(is_staff=True).all())


@admin.register(ReferralNote)
class ReferralNoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'referral', 'note', 'staff', 'created_at')
    form = ReferralNoteAdminForm

    def get_readonly_fields(self, request, obj=None):
        if obj: # editing an existing object
            return self.readonly_fields + ('staff', 'referral', )
        return self.readonly_fields


@admin.register(ReferralNotifications)
class ReferralNotificationsAdmin(admin.ModelAdmin):
    readonly_fields = ('id', 'referral', 'template', 'subject', 'message', 'status', 'created_at')
    list_display = ('id', 'referral', 'template', 'subject', 'status', 'created_at')
    exclude = ('delivered', )


class LawyerReferralEngagementReportsInline(nested_admin.NestedTabularInline):
    model = HistoricalReferralLawyerWorkflowState
    readonly_fields = ('updated_at', 'hours_worked', 'notes', 'is_human_activity', 'referral',)
    exclude = ('workflow_ptr', 'history_change_reason', 'history_date', 'history_type', 'history_relation', 'history_user', 'notification', 'is_overdue')
    extra = 0
    max_num = 0
    verbose_name = 'Engagement Report'
    verbose_name_plural = 'Engagement Reports'

    def get_queryset(self, request):
        qs = super(LawyerReferralEngagementReportsInline, self).get_queryset(request)
        return qs.filter(is_human_activity=True)

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class MediatorReferralEngagementReportsInline(nested_admin.NestedTabularInline):
    model = HistoricalReferralMediatorWorkflowState
    readonly_fields = ('updated_at', 'hours_worked', 'notes', 'is_human_activity', 'referral',)
    exclude = ('workflow_ptr', 'history_change_reason', 'history_date', 'history_type', 'history_relation', 'history_user', 'notification', 'is_overdue')
    extra = 0
    max_num = 0
    verbose_name = 'Engagement Report'
    verbose_name_plural = 'Engagement Reports'

    def get_queryset(self, request):
        qs = super(MediatorReferralEngagementReportsInline, self).get_queryset(request)
        return qs.filter(is_human_activity=True)

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ReferralNotificationsInline(nested_admin.NestedTabularInline):
    model = ReferralNotifications
    readonly_fields = ('subject', 'status', 'template', )
    exclude = ('message', 'delivered')
    show_change_link = True
    extra = 0
    max_num = 0

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ReferralNoteInlineList(nested_admin.NestedTabularInline):
    model = ReferralNote
    show_change_link = True
    readonly_fields = ("note", "staff", )
    extra = 0
    verbose_name = "Note on Referral"
    verbose_name_plural = "All Notes on Referral"

    def has_add_permission(self, request, obj=None):
        return False


class ReferralNoteInlineAdd(nested_admin.NestedTabularInline):
    model = ReferralNote
    form = ReferralNoteAdminForm
    show_change_link = True
    fields = ("note", "staff",)
    extra = 0
    verbose_name = "Add Note on Referral"
    verbose_name_plural = "Add Note on Referral"

    def has_change_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return False


class IsOverDueFilter(admin.SimpleListFilter):
    title = 'Is Matter Overdue?'
    parameter_name = 'is_overdue'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes Overdue'),
            ('no', 'Not Overdue'),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == 'yes':
            return queryset.filter(Q(Q(referrallawyerworkflowstate__isnull=True) &  Q(referralmediatorworkflowstate__is_overdue=True)) | Q(Q(referralmediatorworkflowstate__isnull=True) &  Q(referrallawyerworkflowstate__is_overdue=True)))
        elif value == 'no':
            return queryset.filter(Q(Q(referrallawyerworkflowstate__isnull=True) &  Q(referralmediatorworkflowstate__is_overdue=False)) | Q(Q(referralmediatorworkflowstate__isnull=True) &  Q(referrallawyerworkflowstate__is_overdue=False)))
        return queryset


class LawyerReferralStatusFilter(admin.SimpleListFilter):
    title = 'Lawyer Referral Status?'
    parameter_name = 'lawyer_referral_status'

    def lookups(self, request, model_admin):
        return tuple(ReferralLawyerWorkflowState.pretty_nodes.items())

    def queryset(self, request, queryset):
        value = self.value()
        if value in ReferralLawyerWorkflowState.pretty_nodes.keys():
            return queryset.filter(referrallawyerworkflowstate__current_task__name=value)
        return queryset


class MediatorReferralStatusFilter(admin.SimpleListFilter):
    title = 'Mediator Referral Status?'
    parameter_name = 'mediator_referral_status'

    def lookups(self, request, model_admin):
        return tuple(ReferralMediatorWorkflowState.pretty_nodes.items())

    def queryset(self, request, queryset):
        value = self.value()
        if value in ReferralMediatorWorkflowState.pretty_nodes.keys():
            return queryset.filter(referralmediatorworkflowstate__current_task__name=value)
        return queryset


@admin.register(Referral)
class ReferralAdmin(nested_admin.NestedModelAdmin):
    model = Referral

    list_filter = (IsOverDueFilter, LawyerReferralStatusFilter, MediatorReferralStatusFilter, 'professional',)

    list_display = ('get_date_formatted', 'professional_link', 'referral_type', 'client_name', 'pretty_view', 'update_status', 'is_overdue', 'referral_status', 'email', 'practice_area')
    list_display_links = ('client_name',)

    readonly_fields = ('professional', 'first_name', 'last_name', 'email', 'phone', 'address',
                       'zipcode', 'monthly_income', 'household_size', 'income_status', 'in_dc', 'language', 'practice_area',
                       'issue_description', 'follow_up_consent', 'contact_preference',
                       'deadline_date', 'deadline_reason', 'referred_by', 'created_at', 'referral_type', 'referral_status', 'is_overdue')
    exclude = ('lawyer_notification', 'practice_area')

    inlines = (ReferralNoteInlineList, ReferralNoteInlineAdd, LawyerReferralEngagementReportsInline, MediatorReferralEngagementReportsInline, ReferralNotificationsInline)

    def client_name(self, obj):
        return obj.first_name + " " + obj.last_name

    def practice_area(self, obj):
        pa = PracticeArea.objects.filter(id=obj.practice_area).first()
        return f'{pa.title} ({pa.parent.title})'
    practice_area.short_description = 'Practice Area'

    def get_date_formatted(self, obj):
        return obj.created_at.date()
    get_date_formatted.short_description = 'Recevied At'

    def professional_link(self, obj):
        """ provides link to professional's profile """
        return format_html("<a href='/admin/lowbono_app/user/{id}/change/'>{name}</a>", name=obj.professional.get_full_name(), id=obj.professional.id)
    professional_link.short_description = 'Professional'

    def referral_type(self, obj):
        if hasattr(obj, 'referrallawyerworkflowstate'):
            return "LAWYER"
        if hasattr(obj, 'referralmediatorworkflowstate'):
            return "MEDIATOR"
        return 'Workflow Not Started'
    referral_type.short_description = 'Referral Type'

    def referral_status(self, obj):
        if hasattr(obj, 'referrallawyerworkflowstate'):
            return obj.referrallawyerworkflowstate.get_current_task_pretty_name()
        if hasattr(obj, 'referralmediatorworkflowstate'):
            return obj.referralmediatorworkflowstate.get_current_task_pretty_name()
        return 'Workflow Not Started'
    referral_status.short_description = 'Referral Status'

    def update_status(self, obj):
        """ provides link to status update form on referral, if joeflow state model exists/created """

        if hasattr(obj, 'referrallawyerworkflowstate'):
            _update_url = obj.referrallawyerworkflowstate.workflow_task_update_url()
            if _update_url:
                return format_html("<a href='{url}'>Update</a>", url=_update_url)
            else:
                return "-"
        if hasattr(obj, 'referralmediatorworkflowstate'):
            _update_url = obj.referralmediatorworkflowstate.workflow_task_update_url()
            if _update_url:
                return format_html("<a href='{url}'>Update</a>", url=_update_url)
            else:
                return "-"

    def pretty_view(self, obj):
        return format_html("<a href='/professionals/referrals/{id}'>View</a>", id=obj.id)

    def is_overdue(self, obj):
        if hasattr(obj, 'referrallawyerworkflowstate'):
            if obj.referrallawyerworkflowstate.is_overdue:
                return "Yes"
        if hasattr(obj, 'referralmediatorworkflowstate'):
            if obj.referralmediatorworkflowstate.is_overdue:
                return "Yes"
        return "No"
    is_overdue.short_description = 'Is Matter Overdue?'


@admin.register(LawyerReferral)
class LawyerReferralAdmin(admin.ModelAdmin):
    list_display = ('_referral', 'view_details' )
    readonly_fields = ('_referral', 'referral')

    def view_details(self, obj):
        return format_html("<a href='/admin/lowbono_app/referral/{id}/change/'>View</a>", name=obj.referral, id=obj.referral.id)
    view_details.short_description = 'View Referral Details'

    def _referral(self, obj):
        return obj.referral
    _referral.short_description = 'Lawyer Referral'


@admin.register(MediatorReferral)
class MediatorReferralAdmin(admin.ModelAdmin):
    list_display = ('_referral', 'view_details', 'other_party_first_name', 'other_party_last_name', 'other_party_email', 'other_party_phone',)
    readonly_fields = ('_referral', 'referral')

    def view_details(self, obj):
        return format_html("<a href='/admin/lowbono_app/referral/{id}/change/'>View</a>", name=obj.referral, id=obj.referral.id)
    view_details.short_description = 'View Referral Details'

    def _referral(self, obj):
        return obj.referral
    _referral.short_description = 'Mediator Referral'


class PracticeAreaInline(nested_admin.NestedTabularInline):
    model = PracticeArea
    extra = 0
    max_num = 0
    show_change_link = True
    readonly_fields = ('id', 'title', 'definition', 'parent', 'practicearea_type',)
    exclude = ('title_en', 'definition_en', 'title_es', 'definition_es',)


@admin.register(PracticeAreaCategory)
class PracticeAreaCategoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'definition', 'practicearea_category_type', 'id')
    readonly_fields = ('id',)
    inlines = (PracticeAreaInline, )


@admin.register(PracticeArea)
class PracticeAreaAdmin(admin.ModelAdmin):
    list_display = ('title', 'definition', 'parent', 'practicearea_type', 'id')
    readonly_fields = ('id', 'parent')
    def get_readonly_fields(self, request, obj=None):
        if not obj: # adding new object
            return ()
        return self.readonly_fields


class EmailEventEnterStateAdminForm(forms.ModelForm):
    class Meta:
        model = EmailEventEnterState
        exclude = ()
        widgets = {
            'workflow_state': forms.Select()
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class EmailEventInactiveForAdminForm(forms.ModelForm):
    class Meta:
        model = EmailEventInactiveFor
        exclude = ()
        widgets = {
            'workflow_state': forms.Select()
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class EmailEventDeadlineAdminForm(forms.ModelForm):
    class Meta:
        model = EmailEventDeadline
        exclude = ()
        widgets = {
            'workflow_state': forms.Select()
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


@admin.register(EmailEventEnterState)
class EmailEventEnterStateAdmin(admin.ModelAdmin):
    list_display = ('workflow_state', 'days_after', 'template')
    form = EmailEventEnterStateAdminForm


@admin.register(EmailEventInactiveFor)
class EmailEventInactiveForAdmin(admin.ModelAdmin):
    list_display = ('workflow_state', 'days_inactive', 'template')
    form = EmailEventInactiveForAdminForm


@admin.register(EmailEventDeadline)
class EmailEventDeadlineAdmin(admin.ModelAdmin):
    list_display = ('workflow_state', 'days', 'before_or_after_deadline', 'template')
    form = EmailEventDeadlineAdminForm


class EmailEventEnterStateInlineFormset(forms.models.BaseInlineFormSet):
    def clean(self):
        invalid_state = next((form.cleaned_data.get('workflow_state') for form in self.forms if form.cleaned_data and form.cleaned_data.get('workflow_state') not in self.instance.workflow_type.model_class().pretty_nodes.keys()), None)
        if invalid_state:
            raise ValidationError(f"Please choose a valid workflow state choice for {self.model.__name__}")


class EmailEventInactiveForInlineFormset(forms.models.BaseInlineFormSet):
    def clean(self):
        invalid_state = next((form.cleaned_data.get('workflow_state') for form in self.forms if form.cleaned_data and form.cleaned_data.get('workflow_state') not in self.instance.workflow_type.model_class().pretty_nodes.keys()), None)
        if invalid_state:
            raise ValidationError(f"Please choose a valid workflow state choice for {self.model.__name__}")


class EmailEventDeadlineInlineFormset(forms.models.BaseInlineFormSet):
    def clean(self):
        invalid_state = next((form.cleaned_data.get('workflow_state') for form in self.forms if form.cleaned_data and form.cleaned_data.get('workflow_state') not in self.instance.workflow_type.model_class().pretty_nodes.keys()), None)
        if invalid_state:
            raise ValidationError(f"Please choose a valid workflow state choice for {self.model.__name__}")


class EmailEventEnterStateInline(admin.TabularInline):
    model = EmailEventEnterState
    formset = EmailEventEnterStateInlineFormset
    form = EmailEventEnterStateAdminForm
    can_delete = False


class EmailEventInactiveForInline(admin.TabularInline):
    model = EmailEventInactiveFor
    formset = EmailEventInactiveForInlineFormset
    form = EmailEventInactiveForAdminForm
    can_delete = False


class EmailEventDeadlineInline(admin.TabularInline):
    model = EmailEventDeadline
    formset = EmailEventDeadlineInlineFormset
    form = EmailEventDeadlineAdminForm
    can_delete = False


class EmailTemplateAdminForm(forms.ModelForm):

    class Meta:
        model = EmailTemplates
        exclude = ()
        widgets = {
            'workflow_type': forms.Select(attrs={"hx-get": "/professionals/get_workflow_pretty_nodes/",
                                                 "hx-trigger": "load,change",
                                                 "hx-ext": "multi-swap",
                                                 "hx-swap": "multi:#id_emailevententerstate-0-workflow_state:innerHTML,#id_emaileventinactivefor-0-workflow_state:innerHTML,#id_emaileventdeadline-0-workflow_state:innerHTML"}),
        }

    def clean(self):
        cleaned_data = super().clean()

        if not cleaned_data.get("workflow_type"):
            raise ValidationError(f"Oops, please choose a valid workflow type")

        subject = cleaned_data.get("subject")
        body = cleaned_data.get("body")

        msg = "Fix template errors"

        if not self.template_valid(subject):
            self.add_error('subject', msg)

        if not self.template_valid(body):
            self.add_error('body', msg)

    def template_valid(self, value):
        # TODO: add regex to check {{ vars }} issues
        return True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].label = "What this email is for (description)"
        self.fields['active'].label = "Is this email being sent actively (active)"
        self.fields['workflow_type'].label = "Email for (workflow type)"
        self.fields['workflow_type'].empty_label = "[select workflow]"
        self.fields['recipient'].label = "Send email to (recipient)"
        self.fields['recipient'].widget.attrs['class'] = 'main'
        self.fields['subject'].label = "Email subject"
        self.fields['event_type'].required = True
        self.fields['event_type'].label = "When the following happens? (event type)"
        self.fields['event_type'].widget.attrs['class'] = 'main'


@admin.register(EmailTemplates)
class EmailTemplatesAdmin(admin.ModelAdmin):
    list_display = ('subject', 'description', 'workflow_type_display', 'send_email_to_display',
                    'event_type_display', 'event_condition_display',
                    'pretty_view', 'active')
    inlines = (EmailEventEnterStateInline, EmailEventInactiveForInline, EmailEventDeadlineInline,)
    form = EmailTemplateAdminForm

    def workflow_type_display(self, obj):
        return ''.join(' ' + char if char.isupper() else char.strip() for char in obj.workflow_type.model_class().__name__).strip() if obj.workflow_type else ''
    workflow_type_display.short_description = 'Workflow Type'

    def send_email_to_display(self, obj):
        return obj.recipient if obj.recipient else ''
    send_email_to_display.short_description = 'Send Email To'

    def event_type_display(self, obj):
        return obj.get_event_type_display() if obj.event_type else ''
    event_type_display.short_description = 'When This Event Type Occurs'

    def event_condition_display(self, obj):
        if hasattr(obj, obj.event_type):
            return getattr(obj, obj.event_type)
        return ''
    event_condition_display.short_description = 'Condition To Match for Event'


    class Media:
        js = ('admin/emailtemplates.js', 'htmx/htmx.min.js', 'htmx/multi-swap.js')

    fieldsets = ((None, {
        'fields': (
            ('description', 'active',),
            ('workflow_type', 'recipient',),
            'subject',
            'body',
            'event_type',
        ),
    }),)

    def save_related(self, request, form, formsets, change):
        """
            delete existing instances of formsets, if formset model doesn't match choosen event_type
        """

        for formset in formsets:
            if form.instance.event_type != formset.model.__name__.lower():
                for inline_form in formset:
                    if inline_form.cleaned_data:
                        if inline_form.instance.pk:
                            inline_form.instance.delete()

        super(EmailTemplatesAdmin, self).save_related(request, form, formsets, change)

    def pretty_view(self, obj):
        return format_html("<a href='/professionals/email_template/{id}'>View</a>", id=obj.id)


class SystemEmailEventsInline(admin.TabularInline):
    model = SystemEmailEvents
    can_delete = False


@admin.register(SystemEmailEvents)
class SystemEmailEventsAdmin(admin.ModelAdmin):
    list_display = ('event_name', 'template')


class SystemEmailTemplateAdminForm(forms.ModelForm):

    class Meta:
        model = SystemEmailTemplates
        fields = ('description', 'active', 'subject', 'body')

    def clean(self):
        cleaned_data = super().clean()
        subject = cleaned_data.get("subject")
        body = cleaned_data.get("body")

        msg = "Fix template errors"

        if not self.template_valid(subject):
            self.add_error('subject', msg)

        if not self.template_valid(body):
            self.add_error('body', msg)

    def template_valid(self, value):
        # TODO: add regex to check {{ vars }} issues
        return True


@admin.register(SystemEmailTemplates)
class SystemEmailTemplatesAdmin(admin.ModelAdmin):
    list_display = ('subject', 'description', 'event_name_display', 'active')
    inlines = (SystemEmailEventsInline,)
    form = SystemEmailTemplateAdminForm

    def event_name_display(self, obj):
        return obj.systememailevents.event_name if obj.systememailevents else ''
    event_name_display.short_description = 'Event Name'


@admin.register(EmailAPILogs)
class EmailAPILogsAdmin(admin.ModelAdmin):
    list_display = ('to_email', 'created_at')


@admin.register(CeleryETATasks)
class CeleryETATasksAdmin(admin.ModelAdmin):
    list_display = ('eta', 'func', 'args', 'status', 'created_at')


class ProfileNoteAdminForm(forms.ModelForm):
    class Meta:
        model = ProfileNote
        fields = ('note', 'professional', 'admin')

    def __init__(self, *args, **kwargs):
        super(ProfileNoteAdminForm, self).__init__(*args, **kwargs)
        self.fields['professional'] = forms.ModelChoiceField(queryset=User.objects.filter(is_staff=False).all())
        self.fields['admin'] = forms.ModelChoiceField(queryset=User.objects.filter(is_staff=True).all())


@admin.register(ProfileNote)
class ProfileNoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'note', 'professional', 'created_at')
    form = ProfileNoteAdminForm

    def get_readonly_fields(self, request, obj=None):
        if obj: # editing an existing object
            return self.readonly_fields + ('note', 'professional', )
        return self.readonly_fields


@admin.register(PovertyLineRate)
class PovertyLineRateAdmin(admin.ModelAdmin):
    list_display = ('first_household_member_rate', 'additional_household_member_rate')

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ReferralSource)
class ReferralSourceAdmin(admin.ModelAdmin):
    list_display = ('source',)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LawyerLLMLogs)
class LLMLogsAdmin(admin.ModelAdmin):
    list_display = ('get_short_user_query', 'practice_area_matched', 'llm_result', 'id', 'created_at')
    fields = ('user_query', 'llm_result', 'practice_area_matched', 'lawyer_referral', 'user_prompt', 'instruction_prompt', 'audit_trail', 'id', 'created_at')

    def get_short_user_query(self, obj):
        if len(obj.user_query) > 150:
            return obj.user_query[:150] + " ..."
        return obj.user_query
    get_short_user_query.short_description = "User Query"


    def get_readonly_fields(self, request, obj=None):
        if obj:
            return [field.name for field in obj._meta.fields]
        return []


@admin.register(NewsArticles)
class NewsArticlesAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'created_at')
