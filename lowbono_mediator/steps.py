import datetime
import datetime
from django.utils import timezone

from django.shortcuts import render, redirect
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from . import forms
from lowbono_app import models, steps

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
        context = super().get_context_data(**kwargs)
        context |= {'step': self, 'request': self.request, 'prev_url': self.url(-1), 'next_url': self.url(1), 'skip_url': self.url(2)}
        if self.step in [8, 9]:
            context['skip_url'] = self.url(1)
        return context


class Step1View(BaseStepMixin, FormView):
    heading = _('Do you want a mediator to help you discuss your issue with the other side, to see if you can work out an agreement?')
    before = {
        'body': _('Why choose mediation? <br><br> A mediator is neutral and helps both sides communicate to solve a problem together without going to court. Unlike a lawyer, who advocates for and provides legal advice to only one party, a mediator encourages cooperation and reduces conflict. Mediation is faster, less formal and more affordable. <br><br> Keep in mind that both sides need to agree to participate in mediation. To learn more <a href="/help/what-is-mediation/">click here</a>')
    }
    submit = _('Yes, I want a mediator')
    prev = None
    switch = _('No, I want legal advice')
    switch_url = '/lawyers/1'
    width = 75


class Step2View(BaseStepMixin, FormView):
    heading = _('Would you be comfortable working out an agreement with a mediator, without getting legal advice?')
    before = {
        'body': _('Why don\'t mediators provide legal advice? <br><br> Mediators are neutral. It is not their job to take sides or offer legal advice. They help both sides work together to find a solution without going to court. To learn more <a href="/help/what-is-mediation/">click here</a>')
    }
    submit = _('Yes, I want a mediator')
    switch = _('No, I want legal advice')
    switch_url = '/lawyers/1'
    width = 75


class Step3View(BaseStepMixin, FormView):
    heading = _('Where do you need a mediator?')


class Step4View(BaseStepMixin, FormView):
    heading = _('Do you want to see if you qualify for reduced fees?')
    before = {
        'body': _('Some mediators charge reduced rates depending on your income bracket, which is based on your household size and income. The final determination on reduced fee eligibility will be made by the mediator.')
    }
    submit = _('I want to see if I qualify')
    skip = _('skip')
    after = {
        'heading': _('What income brackets qualify for reduced fees?'),
        'body': _('Reduced fees may be available to people with incomes at or below 400.0% of the <a href="https://aspe.hhs.gov/poverty-guidelines">Federal Poverty Guidelines</a>.\
                   <ul><li>If your household income is less than 400% of the federal poverty guidelines, every mediator and lawyer in our directory promises that, if they accept your case, they will charge no more than $150 per hour or the flat-fee equivalent of that rate for their services, well below the DC average of $380 per hour.</li>\
                   <li>If your household income is too high to qualify for reduced fee services, you may still seek a mediator or lawyer from the DC Refers directory, but they may charge you more than $150 per hour. The final determination on reduced fee eligibility will be made by the mediator or lawyer.</li></ul>'),
    }


class Step5View(BaseStepMixin, FormView):
    heading = _('Do you want to see if you qualify for reduced fees?')
    before = {
        'body': _('Some mediators charge reduced rates depending on your income bracket, which is based on your household size and income. The final determination on reduced fee eligibility will be made by the mediator.')
    }
    submit = _('Update estimate')
    next = _('Continue')
    after = {
        'heading': _('What income brackets qualify for reduced fees?'),
        'body': _('Reduced fees may be available to people with incomes at or below 400.0% of the <a href="https://aspe.hhs.gov/poverty-guidelines">Federal Poverty Guidelines</a>.\
                   <ul><li>If your household income is less than 400% of the federal poverty guidelines, every mediator and lawyer in our directory promises that, if they accept your case, they will charge no more than $150 per hour or the flat-fee equivalent of that rate for their services, well below the DC average of $380 per hour.</li>\
                   <li>If your household income is too high to qualify for reduced fee services, you may still seek a mediator or lawyer from the DC Refers directory, but they may charge you more than $150 per hour. The final determination on reduced fee eligibility will be made by the mediator or lawyer.</li></ul>'),
    }

    alerts = {
        'moderate': _('Based on the information you provided, you qualify for reduced rates from mediators who scale their fees. Click Next to continue.'),
        'low': _('Based on the information you provided, you may qualify for free legal assistance. To find organizations that provide additional assistance, you can visit <a href="https://www.lawhelp.org/dc">www.lawhelp.org/dc</a>. You may also qualify for help from mediators who charge reduced fees. If you would like to connect with a mediator who charges fees, click Next.'),
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


class Step6View(BaseStepMixin, FormView):
    heading = _('What do you need help with?')
    before = {
        'body': _('<ul><li>LowBono is an online directory of mediators and lawyers. Using the DC Refers online directory to try to find help does not establish an attorney-client relationship. Mediators and lawyers may decide not to accept your case for any reason.</li>\
                   <li>LowBono does not guarantee the outcome of any case, or that you will find a mediator or lawyer to take your case, even if your income qualifies you for reduced fee rates.</li></ul>')
    }
    submit = None
    width = 100


class Step7View(BaseStepMixin, FormView):
    form_class = forms.FormPartial(forms.BaseReferralStepForm, ('practice_area',))
    heading = _('Can you tell us more about your issue?')
    submit = None
    width = 100


class Step8View(BaseStepMixin, FormView):
    form_class = forms.FormPartial(forms.BaseReferralStepForm, ('deadline_date', 'deadline_reason',))
    heading = _('Do you have any court appearances or other deadlines coming up?')
    submit = _('Add & Continue')
    skip = _('skip')


class Step9View(BaseStepMixin, FormView):
    form_class = forms.FormPartial(forms.BaseReferralStepForm, ('issue_description',))
    heading = _('Briefly describe your legal issue')
    before = {
        'body': _('Tell the mediator about your legal issue and any opposing parties that are involved in the matter. Please do not provide any sensitive or confidential information here -- those details should only be discussed during your consultation with the mediator. \
                   <ul><li>Mediators and lawyers may charge consultation fees to talk with you and evaluate your case. Consultation fees should be consistent with our reduced fee policy. A mediator may ask you to sign a engagement agreement for an initial consultation.</li>\
                   <li>If a mediator and lawyer takes your case, they will enter into a written engagement agreement with you. The engagement agreement will describe the work the mediator will do for you and the fees the mediator will charge.</li></ul>')
    }
    submit = _('Add & Continue')
    skip = _('skip')
    width = 75


class Step10View(BaseStepMixin, FormView):
    form_class = forms.FormPartial(forms.BaseReferralStepForm, ('professional',))
    heading = _('Who would you like to have a consultation with?')
    heading_no_professionals = _('No mediators found')
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

        from lowbono_mediator.models import MediatorReferral
        from lowbono_mediator.workflows import ReferralMediatorWorkflowState

        MediatorReferral.objects.create(referral=referral, **{key: value for key, value in step_data.items() if 'other_party_' in key})

        ReferralMediatorWorkflowState.referral_received(referral=referral)

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
                    messages.info(request, 'We encourage you to directly contact the mediator, since your court deadline ' + alert_enum[days_remaining])

            out = super().get(request, professional=professional, profile_type="mediator", **additional_context)
            request.session.flush()
            return out
        else:
            request.session.flush()
            return redirect('mediator_step', step=1)
