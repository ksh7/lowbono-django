import os
from django.conf import settings

SECRET_KEY = os.getenv('DJANGO_SECRET')

DEBUG = True

ALLOWED_HOSTS = ['localhost', '*']

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": settings.BASE_DIR / "db.sqlite3",
    },
}

REDIS_CONNECTION_URL = "redis://localhost:6379"
