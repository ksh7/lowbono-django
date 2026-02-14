import os
from .dokku import *

DEBUG = os.getenv('DEBUG_STATUS', 'False') == 'True'

ALLOWED_HOSTS = ['staging.lowbono.org']
CSRF_TRUSTED_ORIGINS = ['https://staging.lowbono.org']

SUPABASE_STORAGE_BUCKET = 'lowbono-staging'

SLACK_BOT_OAUTH_TOKEN = os.getenv('SLACK_BOT_OAUTH_TOKEN')

EMAIL_BACKEND = 'anymail.backends.mailjet.EmailBackend'