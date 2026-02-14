from django.apps import AppConfig


class LowbonoAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'lowbono_app'

    def ready(self):
        from .pluggable_app import PluggableApp
        PluggableApp.autodiscover()
