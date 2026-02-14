from django.utils.translation import gettext_lazy as _
from django.conf import global_settings

NON_EN_LANGUAGES = list(filter(lambda x: x[0] not in ['en', 'en-au', 'en-gb'], global_settings.LANGUAGES))


FIRST_HOUSEHOLD_MEMBER_POVERTY_RATE = 14580  # BASELINE
ADDITIONAL_HOUSEHOLD_MEMBER_POVERTY_RATE = 5140  # MODIFIER incremented based on family size

INCOME_PERIOD_CHOICES = (
    ('monthly', _('Monthly')),
    ('yearly', _('Yearly')),
)

CONTACT_PREFERENCES_CHOICES = (
    ('0', _('Please contact me.')),
    ('1', _('I will contact the Lawyer/Mediator.')),
)

INCOME_STATUS_CHOICES_BEAUTIFY = {
    'low': 'Low Income',
    'moderate': 'Income Eligible',
    'high': 'Market Rate',
    None: 'Not Provided'
}

INCOME_STATUS_CHOICES = (
    ('low', _('Low Income')),
    ('moderate', _('Income Eligible')),
    ('high', _('Market Rate')),
    (None, _('Not Provided')),
)

HOUSEHOLD_SIZE_CHOICES = (
    (1, _('1 person')),
    (2, _('2 people')),
    (3, _('3 people')),
    (4, _('4 people')),
    (5, _('5 people')),
    (6, _('6 people')),
    (7, _('7 people')),
)

COURT_APPEARANCE_MATTER = (
    ('Court hearing', _('Court hearing')),
    ('Filing deadline', _('Filing deadline')),
    ('Statute of limitations', _('Statute of limitations')),
    ('Response due', _('Response due')),
    ('Other/Don\'t know', _('Other/Don\'t know')),
)

CONTACT_REQUEST_LABEL_LAWYER = _("If you request a consultation, do you give the lawyer permission to contact you?")
CONTACT_REQUEST_LABEL_MEDIATOR = _("If you request a consultation, do you give the mediator permission to contact you?")

CONTACT_REQUEST_CHOICES = (
    ('0', _('Yes, they may contact me')),
    ('1', _('No, do not contact me'))
)

FOLLOWUP_REQUEST_LABEL = _("May we follow up with you about your request (for example, with a request summary and survey)")

FOLLOWUP_REQUEST_CHOICES = (
    ('1', _('Yes')),
    ('0', _('No'))
)

HEAR_ABOUT_US_LABEL = _("How did you hear about us?")

HEAR_ABOUT_US_CHOICES = (
    ('Web search', _('Web search')),
    ('Web advertisement', _('Web advertisement')),
    ('Flyer or print advertisement', _('Flyer or print advertisement')),
    ('Community organization', _('Community organization')),
    ('Friend or family', _('Friend or family')),
    ('Government agency', _('Government agency')),
    ('Other', _('Other')),
    ('Bread for the City', _('Bread for the City')),
    ('Children’s Law Center', _('Children’s Law Center')),
    ('DC Affordable Law Firm', _('DC Affordable Law Firm')),
    ('DC Volunteer Lawyers Project', _('DC Volunteer Lawyers Project')),
    ('Legal Counsel for the Elderly', _('Legal Counsel for the Elderly')),
    ('The Legal Aid Society of the District of Columbia', _('The Legal Aid Society of the District of Columbia')),
    ('Washington Legal Clinic for the Homeless', _('Washington Legal Clinic for the Homeless')),
)

MONTHS_LIST = [
    ('1', _('January')),
    ('2', _('February')),
    ('3', _('March')),
    ('4', _('April')),
    ('5', _('May')),
    ('6', _('June')),
    ('7', _('July')),
    ('8', _('August')),
    ('9', _('September')),
    ('10', _('October')),
    ('11', _('November')),
    ('12', _('December'))
]

LOCATION_CHOICES = (
    (True, _('Washington D.C. metropolitan area')),
    (False, _('Somewhere else')),
)

INVITE_CHOICES = (
    ('Lawyer', _('Lawyer')),
    ('Mediator', _('Mediator')),
)

# when to send emails i.e. type of interval
EMAIL_TO_SEND_CHOICES = (
    ('custom', 'Custom'),
    ('initial', 'Initial'),
    ('upcoming', 'Upcoming Time'),
    ('regular', 'Regular'),
)

# whom to send email i.e. to attorney or client
EMAIL_TO_RECIPIENT_CHOICES = (
    (None, "[select recipient]"),
    ('PROFESSIONAL_EMAIL', 'Professional Email'),
    ('CLIENT_EMAIL', 'Client Email'),
)

# email status
EMAIL_STATUS = (
    ('None', 'No Status'),
    ('SENT', 'Sent'), # successfully sent from our system to email service API
    ('FAILED', 'Failed'), # when failed sending by email service API
    ('DELIVERED', 'Delivered'), # delivered to inbox of recipient
)

# income status update from attorney
ATTORNEY_PROVIDED_RATES_BEAUTIFY = {
    True: 'Provided affordable rates to client',
    False: 'Provided standard rates to client',
}