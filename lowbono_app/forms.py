from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.forms.models import inlineformset_factory
from django.forms.widgets import NumberInput
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, HTML, Submit, Field
from crispy_forms.bootstrap import PrependedText

from . import models
from . import constants
from . import widgets

from lowbono_lawyer.models import Lawyer
from lowbono_mediator.models import Mediator


class BaseStepForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False


class StepLocationForm(BaseStepForm):
    in_dc = forms.BooleanField(label=_("Location?"), widget=forms.Select(choices=constants.LOCATION_CHOICES), error_messages={"required": "Outside coverage area: LowBono cannot connect you with Lawyers outside of the Washington D.C. metropolitan area."})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['in_dc'].label = False


class StepIncomeForm(BaseStepForm):
    household_size = forms.ChoiceField(label=_("Household size"), choices=constants.HOUSEHOLD_SIZE_CHOICES)
    monthly_income = forms.IntegerField(label=_("Household income - Monthly ($)"), min_value=0, widget=forms.NumberInput(attrs={'placeholder': 'Monthly household income ($)'}))
    annual_income = forms.CharField(label=_("Annually ($)"), disabled=True, required=False, widget=forms.TextInput(attrs={'placeholder': 'Annual household income ($)'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout = Layout(
            Row(
                'household_size'
            ),
            Row(
                Column(Field(PrependedText('monthly_income', '$'))),
                Column(Field(PrependedText('annual_income', '$')), css_id="id_annual_income_column", style="display:none;"),
            ),
            HTML(
                """
                <script>
                    document.getElementById("id_annual_income_column").style.display = "block";
                    let monthlyIncomeInput = document.getElementById("id_monthly_income");
                    let annualIncomeInput = document.getElementById("id_annual_income");
                    let updateAnnualIncome = function() {
                        let value = parseInt(monthlyIncomeInput.value);
                        if (!isNaN(value)) {
                            annualIncomeInput.value = (value * 12).toLocaleString();
                        }
                    };
                    monthlyIncomeInput.addEventListener("input", updateAnnualIncome);
                    window.addEventListener("load", updateAnnualIncome);
                </script>
                """
            )
        )

    def clean(self):
        cleaned_data = super().clean()
        FIRST_HOUSEHOLD_MEMBER_RATE, ADDITIONAL_HOUSEHOLD_MEMBER_RATE = models.PovertyLineRate.objects.all().values_list('first_household_member_rate', 'additional_household_member_rate')[0]
        poverty_line = FIRST_HOUSEHOLD_MEMBER_RATE + ((int(cleaned_data['household_size']) - 1) * ADDITIONAL_HOUSEHOLD_MEMBER_RATE)
        annual_income = cleaned_data['monthly_income'] * 12
        if annual_income < 2 * poverty_line:
            cleaned_data['income_status'] = 'low'
        elif annual_income > 4 * poverty_line:
            cleaned_data['income_status'] = 'high'
        else:
            cleaned_data['income_status'] = 'moderate'
        return cleaned_data


class StepPracticeAreaCategoryForm(BaseStepForm):
    practice_area_category = forms.ChoiceField(label=_('What do you need help with?'), widget=widgets.RadioPracticeAreaCategorySelect, choices=[('', 'Choose a practice area')])


def FormPartial(BaseForm, _fields):
    """
    Return a new Form that subclasses BaseForm and only contains a subset of the fields.
    """
    class DYNAMIC_FORM(BaseForm):
        class Meta(BaseForm.Meta):
            fields = _fields
    return DYNAMIC_FORM


class ReferralCreateForm(forms.ModelForm):

    class Meta:
        model = models.Referral
        exclude = ()


class SignupForm(forms.ModelForm):
    class Meta:
        model = models.User
        fields = (
            'email',
            'password',
        )


class InviteForm(forms.ModelForm):
    profile_type = forms.ChoiceField(label="User's Profile Type", widget=forms.RadioSelect, choices=[('lawyer', 'Lawyer Only'), ('mediator', 'Mediator Only'), ('both', 'Both Lawyer & Mediator'),])
    class Meta:
        model = models.User
        fields = (
            'email',
            'first_name',
            'last_name',
        )


class ResetPasswordForm(forms.Form):
    email = forms.EmailField(label=_('Email'), max_length=64)


class VacationForm(forms.ModelForm):
    class Meta:
        model = models.Vacation
        fields = (
            'first_day',
            'last_day',
        )
        widgets = {
            'first_day': NumberInput(attrs={'type': 'date'}),
            'last_day': NumberInput(attrs={'type': 'date'}),
        }


class ReferralUpdateForm(forms.ModelForm):

    class Meta:
        model = models.Referral
        fields = ('professional', 'first_name', 'last_name', 'email', "phone", "address",
                  'zipcode', 'income_status', 'in_dc', 'language',
                  'practice_area', 'issue_description', 'follow_up_consent',
                  'contact_preference', 'deadline_date', 'deadline_reason', 'referred_by')


class UserUpdateForm(forms.ModelForm):

    class Meta:
        model = models.User
        fields = ('first_name', 'last_name', 'email', "firm_name", "phone", "address", 'photo', 'bio')

    def __init__(self, initial={}, instance=None, **kwargs):
        base_initial = {}
        base_initial.update(initial)
        super().__init__(initial=base_initial, instance=instance, **kwargs)


class LanguageForm(forms.ModelForm):
    class Meta:
        model = models.Language
        fields = (
            'language',
            'bio',
        )


class BarAdmissionForm(forms.ModelForm):
    class Meta:
        model = models.BarAdmission
        fields = (
            'state',
            'admission_date',
            'bar_number',
        )
        widgets = {
            'admission_date': NumberInput(attrs={'type': 'date'}),
        }


class CustomUserPracticeAreaForm(forms.ModelForm):
    practicearea_type_model = None

    class Meta:
        fields = ('practice_areas',)

    def __init__(self, *args, **kwargs):
        super(CustomUserPracticeAreaForm, self).__init__(*args, **kwargs)

        _queryset = models.PracticeArea.objects.filter(practicearea_type=ContentType.objects.get_for_model(self.practicearea_type_model)).extra(select={'pid': 'CAST(id AS INTEGER)'}).order_by('pid')
        self.fields['practice_areas'] = forms.ModelMultipleChoiceField(queryset=_queryset, widget=widgets.CheckboxSelectMultiplePracticeAreas())

        pa_choices = []
        for pa in models.PracticeAreaCategory.objects.filter(practicearea_category_type=ContentType.objects.get_for_model(self.practicearea_type_model)).extra(select={'pid': 'CAST(id AS INTEGER)'}).order_by('pid'):
            items = []
            for ch in pa.children.all().extra(select={'cid': 'CAST(id AS INTEGER)'}).order_by('cid'):
                items.append((ch.id, ch.title))
            pa_choices.append((pa.title, tuple(items)))

        self.fields['practice_areas'].choices = pa_choices

    def clean(self):
        super().clean()
        if not self.cleaned_data.get('practice_areas'):
            raise ValidationError("Please select practice areas")


class CustomUserLawyerPracticeAreaForm(CustomUserPracticeAreaForm):
    practicearea_type_model = Lawyer

    class Meta:
        model = Lawyer
        fields = ('practice_areas',)


class CustomUserMediatorPracticeAreaForm(CustomUserPracticeAreaForm):
    practicearea_type_model = Mediator

    class Meta:
        model = Mediator
        fields = ('practice_areas',)


class MediationTypeForm(forms.ModelForm):
    class Meta:
        model = Mediator
        fields = ['mediation_type']

## TODO: fix
BarAdmissionFormSet = inlineformset_factory(models.User, models.BarAdmission, form=BarAdmissionForm, fields=('state', 'admission_date', 'bar_number',), extra=0)
BarAdmissionFormSet.add_more = True

LawyerPracticeAreaFormSet = inlineformset_factory(models.User, Lawyer, fields=('practice_areas',), form=CustomUserLawyerPracticeAreaForm, extra=0, can_delete=False)

MediatorPracticeAreaFormSet = inlineformset_factory(models.User, Mediator, fields=('practice_areas',), form=CustomUserMediatorPracticeAreaForm, extra=0, can_delete=False)

LanguageFormSet = inlineformset_factory(models.User, models.Language, fields=('language', 'bio'), extra=0)
LanguageFormSet.add_more = True

ReferralFormSet = inlineformset_factory(models.User, models.Referral, fields=(), extra=0)
ReferralFormSet.add_more = False
