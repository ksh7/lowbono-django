from __future__ import absolute_import, unicode_literals

import os

from django.conf import settings

from celery import Celery
from celery.schedules import crontab


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lowbono.settings')

BASE_REDIS_URL = os.environ.get('REDIS_URL', settings.REDIS_CONNECTION_URL)

app = Celery('lowbono')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

# HACK: we use a custom transport here because the worker polling (using redis BRPOP)
#   has a timeout of 1 that cannot be configured. I was also unable to get a qualified
#   classname to be parsed so we're also hacking the transport aliases in kombu to
#   get our custom class loaded instead of the original class.
#   See: https://docs.celeryq.dev/en/v5.4.0/userguide/configuration.html#broker-url
#   Also see: lowbono.redis_patch:Transport
#   Use for example:
#     "patched-redis://hostname" as the broker scheme instead of "redis://hostname"
# NOTE: keeping this in case we want to experiment in future
# import kombu.transport
# kombu.transport.TRANSPORT_ALIASES["patched-redis"] = "lowbono.redis_patch:Transport"

app.conf.broker_url = BASE_REDIS_URL

app.conf.beat_scheduler = 'django_celery_beat.schedulers.DatabaseScheduler'

app.conf.enable_utc = False

app.conf.timezone = settings.TIME_ZONE

app.conf.beat_schedule = {
    'check-two-times-everyday-crontab': {
        'task': 'send_scheduled_notification_emails',
        'schedule': crontab(hour='10, 17', minute=0,),
    },
    'check-one-time-everyday-crontab': {
        'task': 'send_scheduled_eta_emails',
        'schedule': crontab(hour='11', minute=0,),
    },
    'check-everyhour-crontab': {
        'task': 'celery_health_heartbeat',
        'schedule': crontab(hour='*/1', minute=0,),
    },
    'check-every30min-initiate-missing-workflow-crontab': {
        'task': 'initiate_missing_workflows',
        'schedule': crontab(hour='*/1', minute=0,),
    },
}
