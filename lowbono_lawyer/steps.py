import datetime
from django.utils import timezone
from typing import Any

from django.shortcuts import render, redirect
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.http import HttpRequest, HttpResponse
from django.urls import reverse

from . import forms
from lowbono_app import models, steps
from lowbono_app import tasks

class BaseStepMixin(steps.BaseStepMixin):

    def get_form_class(self):
        """
        Get the form corresponding to the step.
        """
        Form = super().get_form_class() or getattr(forms, f'Step{self.step}Form', None)
        if Form and Form.__name__ == 'DYNAMIC_FORM':
            Form.__name__ = Form.__qualname__ = f'Step{self.step}Form'
        return Form

    def get_context_data(self, **kwargs):
        # Override from steps.BaseStepMixin because
        # mediator also relies on these hardcoded steps 6+7
        context = super().get_context_data(**kwargs)
        context |= {'step': self, 'request': self.request, 'prev_url': self.url(-1), 'next_url': self.url(1), 'skip_url': self.url(2)}
        if self.step in [8, 9]:
            context['skip_url'] = self.url(1)
        return context


class Step1View(BaseStepMixin, FormView):
    heading = _('Where do you need a lawyer?')
    prev = None

    def get_context_data(self, **kwargs):
        referrer = self.request.META.get('HTTP_REFERER', '')
        if '/mediators/1' in referrer or '/mediators/2' in referrer:
            messages.warning(self.request, "If you want legal advice, connecting with a lawyer may be a better place to start. Start below to find a lawyer.")

        return super().get_context_data(**kwargs)


class Step2View(BaseStepMixin, FormView):
    heading = _('Do you want to see if you qualify for reduced fees?')
    before = {
        'body': _('Some lawyers charge reduced rates depending on your income bracket, which is based on your household size and income. The final determination on reduced fee eligibility will be made by the lawyer.')
    }
    submit = _('I want to see if I qualify')
    skip = _('skip')
    after = {
        'heading': _('What income brackets qualify for reduced fees?'),
        'body': _('Reduced fees may be available to people with incomes at or below 400.0% of the <a href="https://aspe.hhs.gov/poverty-guidelines">Federal Poverty Guidelines</a>.\
                   <ul><li>If your household income is less than 400% of the federal poverty guidelines, every lawyer and mediator in our directory promises that, if they accept your case, they will charge no more than $150 per hour or the flat-fee equivalent of that rate for their services, well below the DC average of $380 per hour.</li>\
                   <li>If your household income is too high to qualify for reduced fee services, you may still seek a lawyer or mediator from the DC Refers directory, but they may charge you more than $150 per hour. The final determination on reduced fee eligibility will be made by the lawyer or mediator.</li></ul>'),
    }


class Step3View(BaseStepMixin, FormView):
    heading = _('Do you want to see if you qualify for reduced fees?')
    before = {
        'body': _('Some lawyers charge reduced rates depending on your income bracket, which is based on your household size and income. The final determination on reduced fee eligibility will be made by the lawyer.')
    }
    submit = _('Update estimate')
    next = _('Continue')
    after = {
        'heading': _('What income brackets qualify for reduced fees?'),
        'body': _('Reduced fees may be available to people with incomes at or below 400.0% of the <a href="https://aspe.hhs.gov/poverty-guidelines">Federal Poverty Guidelines</a>.\
                   <ul><li>If your household income is less than 400% of the federal poverty guidelines, every lawyer and mediator in our directory promises that, if they accept your case, they will charge no more than $150 per hour or the flat-fee equivalent of that rate for their services, well below the DC average of $380 per hour.</li>\
                   <li>If your household income is too high to qualify for reduced fee services, you may still seek a lawyer or mediator from the DC Refers directory, but they may charge you more than $150 per hour. The final determination on reduced fee eligibility will be made by the lawyer or mediator.</li></ul>'),
    }

    alerts = {
        'moderate': _('Based on the information you provided, you qualify for reduced rates from lawyers who scale their fees. Click Next to continue.'),
        'low': _('Based on the information you provided, you may qualify for free legal assistance. To find organizations that provide additional assistance, you can visit <a href="https://www.lawhelp.org/dc">www.lawhelp.org/dc</a>. You may also qualify for help from lawyers who charge reduced fees. If you would like to connect with a lawyer who charges fees, click Next.'),
        'high': _('Based on the information you provided, you qualify for market rates. Click Next to continue.')
    }

    def form_valid(self, form):
        """
        We want to display the bound form even if form is valid,
        so call form_valid to ensure form data saved to context,
        but then actually return form_invalid.
        """
        super().form_valid(form)
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        """
        If form is valid, set the alert with the income status info.
        """
        context = super().get_context_data(**kwargs)
        form = context['form']
        if form.is_valid():
            income_status = form.cleaned_data['income_status']
            context['alert'] = self.alerts[income_status]
        return context


class Step4View(BaseStepMixin, FormView):
    form_class = forms.FormPartial(forms.BaseReferralStepForm, ('allow_llm',))
    heading = _('Do you want AI to help you choose a legal category?')
    before = {
        'body': _('The description of your legal issue will be sent to OpenAI servers for analysis. \
                   We will do our best to automatically remove any Personally Identifiable Information prior to submission to OpenAI. <br><br>\
                   If you do not wish to use AI, simply click "Continue without AI" button to proceed.')
    }
    submit = _('I consent')
    skip = _('Continue without AI')

    def get(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        form_cls = forms.FormPartial(forms.BaseReferralStepForm, ('allow_llm',))
        form = form_cls({'allow_llm': False})
        if form.is_valid():
            # If we return to this step, clear out allow_llm field
            self.form_valid(form)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['skip_url'] = self.url(2)
        return context


class Step5View(BaseStepMixin, FormView):
    form_class = forms.FormPartial(forms.BaseReferralStepForm, ('issue_description',))
    heading = _('Briefly describe your legal issue')
    before = {
        'body': _('Tell the lawyer about your legal issue and any opposing parties that are involved in the matter. Please do not provide any sensitive or confidential information here -- those details should only be discussed during your consultation with the lawyer. \
                   <ul><li>Lawyers and mediators may charge consultation fees to talk with you and evaluate your case. Consultation fees should be consistent with our reduced fee policy. A lawyer may ask you to sign a retainer agreement for an initial consultation.</li>\
                   <li>If a lawyer or mediator takes your case, they will enter into a written retainer agreement with you. The retainer agreement will describe the work the lawyer will do for you and the fees the lawyer will charge.</li></ul>')
    }
    submit = _('Add & Continue')
    skip = _('skip')
    width = 75

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["skip_url"] = self.url(1)
        return context

    def post(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        ret = super().post(request, *args, **kwargs)
        step_data = self.request.session.get('step_data', {})
        description = step_data.get('issue_description')
        if description:
            llm_task = tasks.llm_categorize_description.delay(self.request.session.session_key, description, reverse('lawyer_step', kwargs={"step": 7}))
            step_data['llm_decision_task_id'] = llm_task.task_id
            step_data['llm_decision_task_start_time'] = str(datetime.datetime.now())
            self.request.session.modified = True
            return redirect('llm_await')
        return ret

class Step6View(BaseStepMixin, FormView):
    heading = _('What do you need help with?')
    before = {
        'body': _('<ul><li>LowBono is an online directory of lawyers and mediators. Using the DC Refers online directory to try to find help does not establish an attorney-client relationship. Lawyers and mediators may decide not to accept your case for any reason.</li>\
                   <li>LowBono does not guarantee the outcome of any case, or that you will find a lawyer or mediator to take your case, even if your income qualifies you for reduced fee rates.</li></ul>')
    }
    submit = None
    width = 100

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        step_data = self.request.session.get('step_data', {})
        if (step_data.get("allow_llm") == False):
            context["prev_url"] = self.url(-2)
        return context
        

class Step7View(BaseStepMixin, FormView):
    form_class = forms.FormPartial(forms.BaseReferralStepForm, ('practice_area',))
    heading = _('Can you tell us more about your issue?')
    submit = None
    width = 100

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        step_data = self.request.session.get('step_data', {})
        if (step_data.get("llm_decision")):
            del(step_data["llm_decision"])
            self.request.session.modified = True
            from lowbono_app.models import PracticeArea
            category = PracticeArea.objects.get(id=step_data['practice_area'])
            messages.info(self.request, _(f"Our AI recommends '{category.title}' in {category.parent.title} Law"))
            self.heading = f"{category.parent.title} Law"
            self.before = {
                    'body': _(f'Note: If category picked is not suitable, you can <a href="{self.url(-2)}">start over again</a>, or <a href="{self.url(-1)}">manually choose</a> yourself')
            }
            # enable skip button here
            context["skip_url"] = self.url(1)
            self.skip = _("Accept & Continue")
        if (step_data.get("allow_llm") == False):
            context["prev_url"] = self.url(-2)
        return context
        

class Step8View(BaseStepMixin, FormView):
    form_class = forms.FormPartial(forms.BaseReferralStepForm, ('deadline_date', 'deadline_reason',))
    heading = _('Do you have any court appearances or other deadlines coming up?')
    submit = _('Add & Continue')
    skip = _('skip')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        step_data = self.request.session.get('step_data', {})
        if (step_data.get("allow_llm") == True):
            context["skip_url"] = self.url(2)
            context["next_url"] = self.url(2)
        return context


class Step9View(BaseStepMixin, FormView):
    form_class = forms.FormPartial(forms.BaseReferralStepForm, ('issue_description',))
    heading = _('Briefly describe your legal issue')
    before = {
        'body': _('Tell the lawyer about your legal issue and any opposing parties that are involved in the matter. Please do not provide any sensitive or confidential information here -- those details should only be discussed during your consultation with the lawyer. \
                   <ul><li>Lawyers and mediators may charge consultation fees to talk with you and evaluate your case. Consultation fees should be consistent with our reduced fee policy. A lawyer may ask you to sign a retainer agreement for an initial consultation.</li>\
                   <li>If a lawyer or mediator takes your case, they will enter into a written retainer agreement with you. The retainer agreement will describe the work the lawyer will do for you and the fees the lawyer will charge.</li></ul>')
    }
    submit = _('Add & Continue')
    skip = _('skip')
    width = 75


class Step10View(BaseStepMixin, FormView):
    form_class = forms.FormPartial(forms.BaseReferralStepForm, ('professional',))
    heading = _('Who would you like to have a consultation with?')
    heading_no_professionals = _('No lawyers found')
    no_professionals = False
    finish = _('Go to main page')
    width = 100


class Step11View(BaseStepMixin, FormView):
    heading = _('Please enter your contact information to complete your request.')
    submit = _('Request a consultation')
    width = 75

    def form_valid(self, form):
        """
        Save step_data as a new referral using ReferralUpdateForm.
        """
        out = super().form_valid(form)
        step_data = self.request.session.get('step_data', {})
        referral_form = forms.ReferralCreateForm(step_data)
        referral = referral_form.save()

        from lowbono_lawyer.models import LawyerReferral, LawyerLLMLogs
        from lowbono_lawyer.workflows import ReferralLawyerWorkflowState

        lawyer_referral = LawyerReferral.objects.create(referral=referral)
        if step_data.get('lawyer_llm_logs'):
            LawyerLLMLogs.objects.filter(id=step_data['lawyer_llm_logs']).update(lawyer_referral=lawyer_referral)

        ReferralLawyerWorkflowState.referral_received(referral=referral)

        return out


class Step12View(BaseStepMixin, TemplateView):
    success = _('Thanks! Your referral request was successfully received!')
    submit = _('Let us know')
    finish = _('Go to main page')
    prev = None
    after = {
        'note': _('<strong>Note:</strong> If you require an additional referral, you may try submitting another request at a later date. We have emailed you a copy of your request summary. You can also print the summary below for your records.')
    }
    width = 100

    def get(self, request, **additional_context):
        step_data = request.session.setdefault('step_data', {})
        professional_id = step_data.get('professional')
        if professional_id:
            professional = models.User.objects.get(id=professional_id)
            deadline_date_str = step_data.get('deadline_date')
            if deadline_date_str:
                deadline_date = datetime.datetime.strptime(deadline_date_str, '%Y-%m-%d').date()
                if deadline_date < timezone.now().date() + datetime.timedelta(days=3):
                    days_remaining = (deadline_date - timezone.now().date()).days
                    alert_enum = {0: "is today itself", 1: "is tomorrow itself", 2: "is in 2 days", 3: "is in 3 days"}
                    messages.info(request, 'We encourage you to directly contact the lawyer, since your court deadline ' + alert_enum[days_remaining])

            out = super().get(request, professional=professional, profile_type="lawyer", **additional_context)
            request.session.flush()
            return out
        else:
            request.session.flush()
            return redirect('lawyer_step', step=1)
