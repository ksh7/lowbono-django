import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseNotFound, HttpResponse
from django.views.generic.base import TemplateView
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.detail import DetailView
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone, translation
from django.views.generic.list import ListView
from django.db.models import Q, F, Sum
from django.template.loader import render_to_string

from . import models
from . import forms
from . import constants
from . import utils
from . import emails


def loginPage(request):
    """
    Logs in user with Email + Password
    """

    if request.method == 'POST':
        email = request.POST.get('email').lower()
        password = request.POST.get('password')

        user = authenticate(request, email=email, password=password)

        if user is not None:
            # redirect to user details edit page for first time login
            if user.last_login is None and user.is_staff is not True:
                login(request, user)
                return redirect('user-update', id=user.id)
            login(request, user)

            _next = request.GET.get('next', None)
            if _next:
                return redirect(_next)
            if user.is_staff:
                return redirect('/admin')
            return redirect('user-matters', id=user.id)
        else:
            messages.info(request, 'Email OR password is incorrect')

    context = {}

    return render(request, 'lowbono_app/login.html', context)


def logoutUser(request):
    logout(request)
    return redirect('login')


def dashboardPage(request):
    context = {}
    return render(request, 'lowbono_app/dashboard.html', context)


def inviteUserPage(request):
    """
    Creates User and sends invite to email with signup link.
    """

    form = forms.InviteForm()

    if request.method == 'POST':
        form = forms.InviteForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.invite(profile_type=form.cleaned_data['profile_type'])
            messages.info(request, f'Invitation to {user.first_name} {user.last_name} sent successfully!')
            return redirect('professional-list')

    context = {'form': form}
    return render(request, 'lowbono_app/user_invite_form.html', context)


def signupPage(request, token):
    """
    Checks token and allows creating password for invited user.
    """

    user_token = models.Token.objects.filter(token=token).first()

    if user_token is None:
        messages.error(request, 'Oops, invalid signup URL')
        return redirect('/')

    if request.method == 'POST':
        password = request.POST.get('password')

        user = models.User.objects.get(id=user_token.user.id)

        user.password = make_password(password)
        user.save()
        user_token.delete()

        messages.info(request, 'Account created! Please login to access profile')
        return redirect('login')

    context = {}
    return render(request, 'lowbono_app/user_signup_form.html', context)


def resetPasswordPage(request):
    """
    Sends password reset link to user or shows link to staff user.
    """

    form = forms.ResetPasswordForm()

    if request.method == 'POST':
        email = request.POST.get('email').lower()
        user = models.User.objects.filter(email=email).first()
        if user:
            token = models.Token.objects.filter(user=user).first()
            if not token:
                token = models.Token(user=user)
                token.save()

            url = f'{settings.HOST}{token.get_absolute_url()}'

            if request.user.is_staff:
                messages.info(request, f'For {user.get_full_name()}, Password reset link: {url}')
            else:
                template_vars = {"URL": url, "USER_NAME": user.get_full_name()}
                subject, text_content, html_content = utils.generateSystemEmailTemplates(system_email_event='reset-password', template_vars=template_vars)
                emails.send_email(to_email=user.email, subject=subject, text_content=text_content, html_content=html_content)

                messages.info(request, f'Password reset link email sent to {email} Please check your email inbox.')
                return redirect('login')
        else:
            messages.error(request, f'No user found with email {email} Please provide correct email.')

    context = {'form': form}
    return render(request, 'lowbono_app/reset_password_form.html', context)


def emailTemplateView(request, id):
    """
    Pretty HTML view for email template.
    """

    context = {'html_content': utils.generateViewEmailTemplate(id)}

    return render(request, 'lowbono_app/email_template.html', context)


def generateWorkflowStateSelectOptions(pretty_nodes, selected_state):
    html_ele = f"<option disabled {'selected' if not selected_state else ''}>[select a state]</option>"
    for node in pretty_nodes.items():
        if node[0] == selected_state:
            html_ele = html_ele + f"<option selected value='{node[0]}'>{node[1]}</option>"
        else:
            html_ele = html_ele + f"<option value='{node[0]}'>{node[1]}</option>"
    return html_ele


def getWorkflowNodes(request):
    if request.htmx:
        if not request.GET["workflow_type"]:
            return HttpResponse("")

        # checks if EmailTemplate Object exists, and if so, get all existing selected states
        emailevententerstate_selected_state = None
        emaileventinactivefor_selected_state = None
        emaileventdeadline_selected_state = None
        if "/change/" in request.htmx.current_url:
            obj_id = request.htmx.current_url.split("emailtemplates/")[1].split("/change")[0]
            if obj_id:
                template = models.EmailTemplates.objects.get(pk=obj_id)
                if hasattr(template, 'emailevententerstate'):
                    emailevententerstate_selected_state = template.emailevententerstate.workflow_state
                if hasattr(template, 'emaileventinactivefor'):
                    emaileventinactivefor_selected_state = template.emaileventinactivefor.workflow_state
                if hasattr(template, 'emaileventdeadline'):
                    emaileventdeadline_selected_state = template.emaileventdeadline.workflow_state

        pretty_nodes = ContentType.objects.get(pk=request.GET["workflow_type"]).model_class().pretty_nodes

        multi_elements = "<div id='id_emaileventdeadline-0-workflow_state'>" + generateWorkflowStateSelectOptions(pretty_nodes, emaileventdeadline_selected_state) + "</div>" +\
                         "<div id='id_emailevententerstate-0-workflow_state'>" + generateWorkflowStateSelectOptions(pretty_nodes, emailevententerstate_selected_state) + "</div>" + \
                         "<div id='id_emaileventinactivefor-0-workflow_state'>" + generateWorkflowStateSelectOptions(pretty_nodes, emaileventinactivefor_selected_state) + "</div>"

        return HttpResponse(multi_elements)


def getProfessionalByPracticeAreas(request):
    if request.htmx:
        app_name = next(iter(request.GET.keys()), None)
        practicearea_id = request.GET.get(app_name) if app_name else None

        if app_name:
            from .pluggable_app import PluggableApp

            app = PluggableApp.get_app(app_name)
            professional_type = app.name.split("_")[1].capitalize()
            professionals = app._models.Professional.objects.filter(is_enabled=True).order_by('-id')

            if practicearea_id:
                professionals = professionals.filter(practice_areas=practicearea_id)

        return HttpResponse(render_to_string('lowbono_app/professional_detail.html', {'professionals': professionals, 'professional_type': professional_type}))


class UserCustomCanAccessTestMixin(UserPassesTestMixin):

    def handle_no_permission(self):
        messages.error(self.request, 'Oops! You do not have permission to access this page')
        return redirect('dashboard')


class UserByIdCanAccessTestMixin(UserCustomCanAccessTestMixin):

    def test_func(self):
        if self.request.user.is_staff: return True
        return self.request.user.id == int(self.kwargs['id'])


class UserBySlugCanAccessTestMixin(UserCustomCanAccessTestMixin):

    def test_func(self):
        if self.request.user.is_staff: return True
        return self.request.user.id == int(self.kwargs['user_id'])


class UserDetailView(UserByIdCanAccessTestMixin, DetailView):
    model = models.User
    template_name_suffix = '_detail'
    slug_field = 'id'
    slug_url_kwarg = 'id'


class UserUpdateView(UserByIdCanAccessTestMixin, UpdateView):
    model = models.User
    template_name_suffix = '_update_form'
    slug_field = 'id'
    slug_url_kwarg = 'id'
    form_class = forms.UserUpdateForm

    formset_lawyer_practicearea_class = forms.LawyerPracticeAreaFormSet
    formset_mediator_practicearea_class = forms.MediatorPracticeAreaFormSet
    formset_bio_class = forms.LanguageFormSet
    formset_bar_class = forms.BarAdmissionFormSet

    def get_object(self, *args, **kwargs):
        obj = super(UserUpdateView, self).get_object(*args, **kwargs)
        return obj

    def get_success_url(self):
        return self.object.get_absolute_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['formset_lawyer_practicearea'] = self.get_formset_lawyer_practicearea()
        context['formset_mediator_practicearea'] = self.get_formset_mediator_practicearea()
        context['form_mediation_type'] = self.get_form_mediation_type()
        context['formset_bio'] = self.get_formset_bio()
        context['formset_bar'] = self.get_formset_bar()
        return context

    def get_formset_lawyer_practicearea(self, *formset_lawyer_practicearea_class):
        if not formset_lawyer_practicearea_class:
            formset_lawyer_practicearea_class = self.formset_lawyer_practicearea_class

        object = self.get_object()
        kwargs = {
            'instance': object,
        }
        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })

        return formset_lawyer_practicearea_class(**kwargs)

    def get_formset_mediator_practicearea(self, *formset_mediator_practicearea_class):
        if not formset_mediator_practicearea_class:
            formset_mediator_practicearea_class = self.formset_mediator_practicearea_class

        object = self.get_object()
        kwargs = {
            'instance': object,
        }
        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })

        return formset_mediator_practicearea_class(**kwargs)

    def get_form_mediation_type(self):
        if hasattr(self.object, 'mediator_user'):
            mediator = self.object.mediator_user
            if self.request.method in ('POST', 'PUT'):
                return forms.MediationTypeForm(self.request.POST, instance=mediator)
            else:
                return forms.MediationTypeForm(instance=mediator)
        return None

    def get_formset_bio(self, *formset_bio_class):
        if not formset_bio_class:
            formset_bio_class = self.formset_bio_class

        object = self.get_object()
        kwargs = {
            'instance': object,
        }
        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })

        return formset_bio_class(**kwargs)

    def get_formset_bar(self, *formset_bar_class):
        if not formset_bar_class:
            formset_bar_class = self.formset_bar_class

        object = self.get_object()
        kwargs = {
            'instance': object,
        }
        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })

        return formset_bar_class(**kwargs)

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests: instantiate a form instance with the passed
        POST variables and then check if it's valid.
        """
        self.object = self.get_object()
        form = self.get_form()
        formset_bio = self.get_formset_bio()
        formset_lawyer_practicearea = self.get_formset_lawyer_practicearea()
        formset_mediator_practicearea = self.get_formset_mediator_practicearea()
        form_mediation_type = self.get_form_mediation_type()
        formset_bar = self.get_formset_bar()

        if form.is_valid() and formset_bio.is_valid() and formset_bar.is_valid():
            if hasattr(self.object, 'lawyer_user') and hasattr(self.object, 'mediator_user') and formset_lawyer_practicearea.is_valid() and formset_mediator_practicearea.is_valid() and form_mediation_type.is_valid():
                return self.form_valid(form, formset_lawyer_practicearea, formset_mediator_practicearea, form_mediation_type, formset_bio, formset_bar)
            elif hasattr(self.object, 'lawyer_user') and formset_lawyer_practicearea.is_valid():
                return self.form_valid(form, formset_lawyer_practicearea, formset_mediator_practicearea, form_mediation_type, formset_bio, formset_bar)
            elif hasattr(self.object, 'mediator_user') and formset_mediator_practicearea.is_valid() and form_mediation_type.is_valid():
                return self.form_valid(form, formset_lawyer_practicearea, formset_mediator_practicearea, form_mediation_type, formset_bio, formset_bar)
            else:
                return self.form_invalid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form, formset_lawyer_practicearea, formset_mediator_practicearea, form_mediation_type, formset_bio, formset_bar):
        formset_lawyer_practicearea.save()
        formset_mediator_practicearea.save()
        if form_mediation_type:
            form_mediation_type.save()
        formset_bio.save()
        formset_bar.save()
        return super().form_valid(form)


class VacationList(UserBySlugCanAccessTestMixin, ListView):

    def get_queryset(self):
        return models.Vacation.objects.filter(user__id=self.kwargs['user_id']).order_by('-last_day')


class VacationUpdateView(UserBySlugCanAccessTestMixin, UpdateView):
    model = models.Vacation
    form_class = forms.VacationForm
    slug_field = 'id'
    slug_url_kwarg = 'id'
    template_name_suffix = '_update_form'

    def get_success_url(self):
        return reverse('vacations', args=[self.kwargs['user_id']])

    def get_queryset(self):
        return models.Vacation.objects.filter(user__id=self.kwargs['user_id'])


class VacationCreateView(UserBySlugCanAccessTestMixin, CreateView):
    model = models.Vacation
    form_class = forms.VacationForm
    slug_field = 'id'
    slug_url_kwarg = 'id'
    template_name_suffix = '_create_form'

    def get_success_url(self):
        return reverse('vacations', args=[self.kwargs['user_id']])

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.save()
        return super().form_valid(form)


class ProfessionalListView(TemplateView):

    template_name = "lowbono_app/professional_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        from .pluggable_app import PluggableApp

        context['professional_apps'] = []
        is_active_view = False

        for app in PluggableApp.get_apps():

            query_param_key = f"{app.name.split("_")[1][0]}pa"
            query_param_value = self.request.GET.get(query_param_key)

            app_context = {
                "app_name": app.name,
                "professional_type": app.name.split("_")[1].capitalize(),
                "query_param_key": query_param_key,
                'professionals': app._models.Professional.objects.filter(is_enabled=True).order_by('-id'),
                "practiceareas": models.PracticeAreaCategory.objects.filter(practicearea_category_type=ContentType.objects.get_for_model(app._models.Professional)),
            }

            if query_param_value:
                app_context['professionals'] = app_context['professionals'].filter(practice_areas=query_param_value)
                context[query_param_key] = query_param_value
                app_context['selected_pa'] = query_param_value
                app_context['is_active'] = True
                is_active_view = True
            else:
                app_context['selected_pa'] = None
                app_context['is_active'] = False

            context['professional_apps'].append(app_context)

        if not is_active_view and context['professional_apps']:
            context['professional_apps'][0]['is_active'] = True

        return context


class ReferralUpdateView(UserCustomCanAccessTestMixin, UpdateView):
    model = models.Referral
    template_name_suffix = '_update_form'
    slug_field = 'id'
    slug_url_kwarg = 'id'
    form_class = forms.ReferralUpdateForm

    def test_func(self, *args, **kwargs):
        if self.request.user.is_staff: return True
        obj = super(ReferralUpdateView, self).get_object(*args, **kwargs)
        return self.request.user.id == obj.professional.id


class ReferralDetailView(UserCustomCanAccessTestMixin, DetailView):
    model = models.Referral
    template_name_suffix = '_detail'
    slug_field = 'id'
    slug_url_kwarg = 'id'

    def test_func(self, *args, **kwargs):
        if self.request.user.is_staff: return True
        obj = super(ReferralDetailView, self).get_object(*args, **kwargs)
        return self.request.user.id == obj.professional.id

    def get_context_data(self, **kwargs):
        context = super(ReferralDetailView, self).get_context_data(**kwargs)
        
        context['referral_type'] = None
        context['referral_workflow'] = None
        context['template'] = ''
        context['notification_logs'] = []
        context['engagement_reports'] = []
        context['engagement_reported_hours'] = []

        from .pluggable_app import PluggableApp

        for app in PluggableApp.get_apps():
            referral_workflow = app._models.ReferralWorkflowState.objects.filter(referral=self.object).first()
            if referral_workflow:
                context['referral_workflow'] = referral_workflow
                context['referral_type'] = app.name
                context['professional_type'] = app.name.split("_")[1].capitalize()
                context['template'] = app.name + '/referral_detail.html',

                context['engagement_reports'] = referral_workflow.get_engagement_reports_for_professionals()
                context['engagement_reported_hours'] = referral_workflow.count_total_reported_hours()

                notification_logs = []
                for log in self.object.referralnotifications_set.filter(template__recipient='PROFESSIONAL_EMAIL').order_by('-created_at'):
                    notification_logs.append({'sent_for': log.template.description,
                                            'sent_at': log.created_at})

                context['notification_logs'] = notification_logs

                # additional logs if admin user
                if self.request.user.is_staff:
                    all_logs = []
                    for log in referral_workflow.get_engagement_reports_for_staff():
                        all_logs.append({
                            'type': 'status_report',
                            'report_status': log.history_object.get_current_task_pretty_name(),
                            'hours_worked': log.hours_worked,
                            'notes': log.notes,
                            'timestamp': log.updated_at,
                        })

                    for log in self.object.referralnotifications_set.filter(template__recipient='PROFESSIONAL_EMAIL').order_by('-created_at'):
                        all_logs.append({
                            'type': 'notification',
                            'email_type': log.template.description,
                            'timestamp': log.created_at
                        })

                    context['all_admin_logs'] = sorted(all_logs, key=lambda x: x["timestamp"], reverse=True)
                break

        return context


class UserMatterListView(UserByIdCanAccessTestMixin, ListView):
    model = models.Referral
    slug_field = 'id'
    slug_url_kwarg = 'id'
    ordering = ['-created_at']
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super(UserMatterListView, self).get_context_data(**kwargs)

        context['professional'] = models.User.objects.filter(id=self.kwargs['id']).first()
        context['matters'] = []

        from .pluggable_app import PluggableApp

        for app in PluggableApp.get_apps():
            _profile_exists = app._models.Professional.objects.filter(user=context['professional']).first()
            name = app.name
            overdue = []
            pending = []
            closed = []
            for workflow in app._models.ReferralWorkflowState.objects.filter(referral__professional__id=self.kwargs['id']):
                if workflow.is_referral_ongoing():
                    if workflow.is_overdue:
                        overdue.append(workflow)
                    else:
                        pending.append(workflow)
                else:
                    closed.append(workflow)

            context['matters'].append({
                'name': app.name,
                'professional_type': app.name.split("_")[1].capitalize(),
                'profile_exists': _profile_exists,
                'is_profile_complete': _profile_exists._is_profile_complete() if _profile_exists else False,
                'profile_incomplete_template': 'lowbono_app/profile_incomplete.html',
                'template': 'lowbono_app/referral_list_items.html',
                'pending': pending,
                'overdue': overdue,
                'closed': closed,
            })

        return context
