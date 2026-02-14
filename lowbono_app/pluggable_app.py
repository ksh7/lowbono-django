from abc import ABC, abstractmethod
from django.conf import settings
from django.apps import apps, AppConfig
from django.core.exceptions import ImproperlyConfigured
import inspect


class PluggableModels:
    """Provides access to specific model subclasses"""

    def __init__(self, app_config):
        self._app_config = app_config

    def _get_model_subclass(self, base_model_name):
        """Get the subclass of a base model in this app"""
        return next(
            (model for model in apps.get_app_config(self._app_config.name).get_models()
            if model.__name__ != base_model_name and any(base.__name__ == base_model_name for base in model.__mro__[1:])),
            None
        )

    def _get_model_by_suffix(self, suffix):
        """
            Get a model by matching suffix pattern.
            Finds any model ending with the given suffix.
        """
        return next(
            (model for model in apps.get_app_config(self._app_config.name).get_models()
            if model.__name__.endswith(suffix)),
            None
        )

    @property
    def ReferralWorkflowState(self):
        """Return the ReferralWorkflowStateBase subclass"""
        return self._get_model_subclass('ReferralWorkflowStateBase')

    @property
    def Professional(self):
        """Return the Professional subclass"""
        return self._get_model_subclass('Professional')

    @property
    def Referral(self):
        """Return the {AppPrefix}Referral model (e.g., LawyerReferral, MediatorReferral)."""
        return self._get_model_by_suffix('Referral')


class PluggableApp(ABC):

    _registry = {}
    _registry_initialized = False

    @property
    def _models(self):
        """Lazy-loaded pluggable models"""
        if not hasattr(self, '_pluggable_models'):
            self._pluggable_models = PluggableModels(self)
        return self._pluggable_models

    @classmethod
    def autodiscover(cls):
        """Discover and register all pluggable apps."""
        if cls._registry_initialized:
            return

        for app_name in settings.INSTALLED_PROFESSIONAL_APPS:
            try:
                app_config = apps.get_app_config(app_name.split('.')[-1])

                if not isinstance(app_config, cls):
                    raise ImproperlyConfigured(
                        f"App '{app_name}' must inherit from PluggableApp"
                    )

                cls._registry[app_name] = app_config
            except LookupError:
                raise ImproperlyConfigured(f"App '{app_name}' is not installed.")

        cls._registry_initialized = True

    @classmethod
    def get_apps(cls):
        """Get all registered pluggable apps."""
        cls.autodiscover()
        return cls._registry.values()

    @classmethod
    def get_app(cls, app_name):
        """Get a specific pluggable app by name."""
        cls.autodiscover()
        return cls._registry.get(app_name)
