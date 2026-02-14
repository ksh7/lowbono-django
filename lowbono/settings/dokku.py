"""
Django settings for lowbono Dokku server app.
It is commonly used for both production and staging server
"""

import os

import logging
from django.core.mail import send_mail, EmailMultiAlternatives, get_connection
from django.conf import settings

SECRET_KEY = os.getenv('DJANGO_SECRET')

DEBUG = os.getenv('DEBUG_STATUS', 'False') == 'True'

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": settings.BASE_DIR / "db.sqlite3",
    },
}

REDIS_CONNECTION_URL = os.getenv('REDIS_URL')

STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

HOST = 'https://lowbono.org'

EMAIL_BACKEND = 'anymail.backends.sendinblue.EmailBackend'

ANYMAIL = {
    'SENDINBLUE_API_KEY': os.getenv('SENDINBLUE_EMAIL_API'),
    'MAILJET_API_KEY': os.getenv('MAILJET_EMAIL_API_KEY'),
    'MAILJET_SECRET_KEY': os.getenv('MAILJET_EMAIL_SECRET_KEY'),
}

SLACK_CHANNEL_NAME = "#fire"

class WarningEmailLogger(logging.Handler):
    def emit(self, record):
        to_email = "a1@lowbono.org"
        subject = f"Warning log captured on lowbono-production"

        msg = EmailMultiAlternatives(to=[to_email], subject=subject, body=self.format(record),
                                     from_email=settings.EMAIL_ALIAS, reply_to=[settings.EMAIL_ALIAS])
        msg.attach_alternative(self.format(record), "text/html")
        msg.connection = get_connection('anymail.backends.mailjet.EmailBackend')
        msg.send()


class WarningSlackLogger(logging.Handler):
    def emit(self, record):
        from lowbono.slack import send_slack_alert
        send_slack_alert(SLACK_CHANNEL_NAME, self.format(record))


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': 'django_warning.log',
        },
        'mail_admin': {
            'level': 'WARNING',
            'class': 'lowbono.settings.dokku.WarningEmailLogger',
        },
        'slack_admin': {
            'level': 'WARNING',
            'class': 'lowbono.settings.dokku.WarningSlackLogger',
        },
        'file_llm': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': 'llm_warning.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': True,
        },
        'joeflow_log': {
            'handlers': ['slack_admin'],
            'level': 'WARNING',
            'propagate': False,
        },
        'llm_log': {
            'handlers': ['file_llm'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

DEFAULT_FROM_EMAIL = 'support@lowbono.org'
SERVER_EMAIL = 'support@lowbono.org'

# supabase
SUPABASE_INSTANCE_URL = os.getenv('SUPABASE_INSTANCE_URL')
SUPABASE_STORAGE_KEY = os.getenv('SUPABASE_STORAGE_KEY')

DEFAULT_FILE_STORAGE = 'lowbono.storage.supabase.SupabaseCustomStorage'

DATA_UPLOAD_MAX_NUMBER_FIELDS = 5000
