from django.apps import AppConfig
from lowbono_app.pluggable_app import PluggableApp


class LowbonoLawyerConfig(AppConfig, PluggableApp):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'lowbono_lawyer'
