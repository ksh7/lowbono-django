from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.contrib.contenttypes.models import ContentType
from django.forms.widgets import NumberInput
from phonenumber_field.formfields import PhoneNumberField
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, HTML, Submit, Field

from lowbono_app import models, constants, widgets, utils
from lowbono_app.forms import BaseStepForm, StepLocationForm, StepIncomeForm, StepPracticeAreaCategoryForm, FormPartial, ReferralCreateForm

from lowbono_mediator.models import Mediator, MediatorReferral


class Step1Form(BaseStepForm):
    pass


class Step2Form(BaseStepForm):
    pass


class Step3Form(StepLocationForm):
    pass


class Step4Form(BaseStepForm):
    pass


class Step5Form(StepIncomeForm):
    pass


class Step6Form(StepPracticeAreaCategoryForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        practice_area_category_choices = []
        for practice in models.PracticeAreaCategory.objects.filter(practicearea_category_type=ContentType.objects.get_for_model(Mediator)).extra(select={'pid': 'CAST(id AS INTEGER)'}).order_by('pid'):
            practice_area_category_choices.append((practice.id, practice))
        self.fields['practice_area_category'] = forms.ChoiceField(label=_('What do you need help with?'), widget=widgets.RadioPracticeAreaCategorySelect, choices=practice_area_category_choices)
        self.fields['practice_area_category'].label = False


class BaseReferralStepForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.fields.get('deadline_date', forms.Field()).validators = [MinValueValidator(lambda: timezone.now().date(), _('Oops, you cannot choose a past date. Please choose a suitable date i.e. today or in future, if relevant.'))]

        practice_area_field = self.fields.get('practice_area')
        if practice_area_field is not None:
            practice_area_category_id = kwargs.get('initial', {}).get('practice_area_category')
            practice_areas = models.PracticeArea.objects.filter(parent_id=practice_area_category_id)
            practice_area_field.widget.choices = [(p.id, p) for p in practice_areas]
            practice_area_field.label = False

        issue_description_field = self.fields.get('issue_description')
        if issue_description_field:
            issue_description_field.label = False

        professional_field = self.fields.get('professional')
        if professional_field:
            practice_area = kwargs.get('initial', {}).get('practice_area')
            professionals = utils.filterMediators(practice_area=practice_area)
            professional_field.choices = professionals
            professional_field.label = False

    def clean(self):
        cleaned_data = super().clean()
        practice_area = cleaned_data.get('practice_area')
        if practice_area and not Mediator.objects.get_mediator_matches(practice_area).count():
                raise ValidationError(_('We are sorry, there are no mediators in the LowBono network who match your search. Please try searching again or look at our resources page for other resources.'))

        return cleaned_data

    class Meta:
        model = models.Referral
        fields = ()
        widgets = {
            'practice_area_category': widgets.RadioPracticeAreaCategorySelect,
            'practice_area': widgets.RadioPracticeAreaSelect,
            'deadline_date': NumberInput(attrs={'type': 'date'}),
            'professional': widgets.RadioMediatorDetailSelect,
            'email': forms.TextInput(attrs={'type': 'email'}),
            'address': forms.Textarea(attrs={'rows': '3'})
        }


class Step11Form(BaseReferralStepForm):
    # override default so we don't get ------ as first of three choicese.
    contact_preference = forms.ChoiceField(label=constants.CONTACT_REQUEST_LABEL_MEDIATOR, widget=forms.RadioSelect, choices=constants.CONTACT_REQUEST_CHOICES)
    # override default so it is required.
    follow_up_consent = forms.ChoiceField(label=constants.FOLLOWUP_REQUEST_LABEL, widget=forms.RadioSelect, choices=constants.FOLLOWUP_REQUEST_CHOICES)

    other_party_first_name = forms.CharField(label=_("Other Party's First Name"), max_length=150, required=False)
    other_party_last_name = forms.CharField(label=_("Other Party's Last Name"), max_length=150, required=False)
    other_party_email = forms.EmailField(label=_("Other Party's Email"), required=False)
    other_party_phone = PhoneNumberField(label=_("Other Party's Phone"), required=False)
    other_party_address = forms.CharField(label=_("Other Party's Address"), widget=forms.Textarea(attrs={'rows': '3'}), required=False)

    class Meta(BaseReferralStepForm.Meta):
        fields = ['first_name', 'last_name', 'email', 'phone', 'language', 'address',
                  'other_party_first_name', 'other_party_last_name', 'other_party_email', 'other_party_phone', 'other_party_address', 
                  'contact_preference', 'follow_up_consent', 'referred_by']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout = Layout(
            Row(
                Column('first_name'),
                Column('last_name'),
            ),
            Row(
                Column('email'),
                Column('phone'),
            ),
            Row(
                Column('address'),
                Column('language'),
            ),
            HTML("""
                <br><h4>Other Party's Contact Details</h4><p class='small'>Please provide details of other party to mediation, if available.</p><hr>
                """
            ),
            Row(
                Column('other_party_first_name'),
                Column('other_party_last_name'),
            ),
            Row(
                Column('other_party_email'),
                Column('other_party_phone'),
            ),
            Row(
                Column('other_party_address'),
                Column()
            ),
            HTML("""
                <br><h4>Additional information</h4><hr>
                """
            ),
            Row(
                Column('contact_preference'),
            ),
            Row(
                Column('follow_up_consent'),
            ),
            Row(
                Column('referred_by', css_class="col-md-6"),
            ),
            HTML("""
                <script>
                    document.querySelector("form").addEventListener("submit", function(event) {
                        document.querySelector("button[type='submit']").setAttribute("disabled", "disabled");
                    });
                </script>
                """
              )
        )
