import datetime

from django.conf import global_settings
from django import template
from lowbono_app import constants
from lowbono_app import models
from django.utils import timezone, timesince
from localflavor.us.models import STATE_CHOICES

register = template.Library()


@register.filter(name='subject_icon_exists')
def subject_icon_exists(value):
	if int(value) in [1, 2, 3, 4, 5, 6, 7, 8, 9, 24, 25, 26, 27, 28, 29]:
		return True
	return False

@register.filter(name='beautify_income_status')
def beautify_income_status(value):
	return constants.INCOME_STATUS_CHOICES_BEAUTIFY[value]

@register.filter(name='beautify_attorney_provided_rates')
def beautify_attorney_provided_rates(value):
	return constants.ATTORNEY_PROVIDED_RATES_BEAUTIFY[value]

@register.filter(name='beautify_language_code')
def beautify_language_code(value):
	for lang in global_settings.LANGUAGES:
		if value == lang[0]:
			return lang[1]

	return ''

@register.filter(name='beautify_bar_location_code')
def beautify_bar_location_code(value):
	for state in STATE_CHOICES:
		if value == state[0]:
			return state[1]

	return ''

@register.filter(name='count_selected_options')
def count_selected_options(options):
	return sum(1 for item in options if item['selected'])

@register.filter(name='pretty_date_custom')
def pretty_date_custom(value):
    "shows 'just now' upto 60 seconds minutes/hours/days ago upto 7 days exact date for greater than 7 days"
    if isinstance(value, datetime.datetime):
        time_diff = timezone.now() - value
        if time_diff > datetime.timedelta(days=7):
            return value.strftime("%b %d, %Y")
        return "Just now" if time_diff.total_seconds() < 60 else timesince.timesince(value) + " ago"
    return value

@register.filter(name='pretty_date_bulk_update_template')
def pretty_date_bulk_update_template(value):
    """Convert a datetime object to a human-readable relative time string."""
    if value is None:
        return 'Never'

    if isinstance(value, datetime.datetime):
        time_diff = timezone.now() - value
        if time_diff > datetime.timedelta(days=30):
            return value.strftime("%b %d, %Y")
        return "Recently Updated" if time_diff.days < 3 else f"{time_diff.days} days ago"
    return value
