from datetime import date

from django import forms
from django.forms.widgets import ChoiceWidget

from .constants import MONTHS_LIST


class RadioPracticeAreaCategorySelect(ChoiceWidget):
    input_type = 'radio'
    template_name = 'lowbono_app/custom_practicearea_categories.html'
    option_template_name = 'lowbono_app/custom_practicearea_categories_options.html'


class RadioPracticeAreaSelect(ChoiceWidget):
    input_type = 'radio'
    template_name = 'lowbono_app/custom_practice_areas.html'
    option_template_name = 'lowbono_app/custom_practice_areas_options.html'


class RadioLawyerDetailSelect(ChoiceWidget):
    input_type = 'radio'
    template_name = 'lowbono_app/custom_professionals.html'
    option_template_name = 'lowbono_app/custom_lawyers_options.html'


class RadioMediatorDetailSelect(ChoiceWidget):
    input_type = 'radio'
    template_name = 'lowbono_app/custom_professionals.html'
    option_template_name = 'lowbono_app/custom_mediators_options.html'


class CheckboxSelectMultiplePracticeAreas(ChoiceWidget):
    allow_multiple_selected = True
    input_type = "checkbox"
    template_name = 'lowbono_app/custom_practicearea_checkbox.html'
    option_template_name = 'lowbono_app/custom_practicearea_checkbox_option.html'
    use_fieldset = True

    def id_for_label(self, id_, index=None):
        if index is None:
            return ""
        return super().id_for_label(id_, index)

    def use_required_attribute(self, initial):
        return False

    def value_omitted_from_data(self, data, files, name):
        return False

class DateSelectorWidget(forms.MultiWidget):
    def __init__(self, attrs=None):
        days = [(day, day) for day in range(1, 32)]
        months = MONTHS_LIST
        years = [(year, year) for year in [2020, 2021, 2022, 2023, 2024]]
        widgets = [
            forms.Select(attrs=attrs, choices=days),
            forms.Select(attrs=attrs, choices=months),
            forms.Select(attrs=attrs, choices=years),
        ]
        super().__init__(widgets, attrs)

    def decompress(self, value):
        if isinstance(value, date):
            return [value.day, value.month, value.year]
        elif isinstance(value, str):
            year, month, day = value.split('-')
            return [day, month, year]
        return [None, None, None]

    def value_from_datadict(self, data, files, name):
        day, month, year = super().value_from_datadict(data, files, name)
        # DateField expects a single string that it can parse into a date.
        print(day, month, year)
        return '{}-{}-{}'.format(year, month, day)
