import datetime
from typing import Any
import datetime
from phonenumber_field.modelfields import PhoneNumber
from django.db.models import Model

from django.shortcuts import redirect
from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.http import HttpRequest, HttpResponse


class BaseStepMixin():
    submit = _('Continue')
    prev = _('back')
    width = 50
    viewname = None

    required_session_keys = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.viewname = self.__module__.split('.')[0].split('_')[-1] + '_step'

    @property
    def step(self):
        cls_name = self.__class__.__name__
        step = int(cls_name.removeprefix('Step').removesuffix('View'))
        return step

    def get(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        if not self._session_keys_available(request):
            return redirect(self.viewname, step=1)
        return super().get(request, *args, **kwargs)

    def post(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        if not self._session_keys_available(request):
            return redirect(self.viewname, step=1)
        return super().post(request, *args, **kwargs)

    def get_initial(self):
        """
        Get initial data for form. Default to getting it from
        the session's `step_data`.
        """
        return self.request.session.get('step_data', {})

    def url(self, index=0):
        """
        Return the url of the step at index relative to this step.
        Thus, if this is step 4, url(index=2) would return step 6,
        url(index=-2) would return step 2 and url() would return 4.
        """
        return reverse(self.viewname, args=[self.step + index])

    def get_success_url(self):
        return reverse(self.viewname, args=[self.step + 1])
    
    def form_valid(self, form):
        """
        Save form data to session if form is valid.
        """
        step_data = self.request.session.setdefault('step_data', {})
        step_data |= _serialize(form.cleaned_data)
        self.request.session.modified = True
        return super().form_valid(form)

    def get_template_names(self):
        try:
            return super().get_template_names()
        except ImproperlyConfigured:
            return (f'steps/{self.step}.html', 'steps/default.html')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context |= {'step': self, 'request': self.request, 'prev_url': self.url(-1), 'next_url': self.url(1), 'skip_url': self.url(2)}
        if self.step in [6, 7]:
            context['skip_url'] = self.url(1)
        return context

    def _session_keys_available(self, request):
        """
            Deals with session expiry after 15 minutes, and jumping steps without filling previous steps
            checks session to ensure relevant keys are available at relevant steps, else return False
        """
        if not request.user.is_authenticated:
            request.session.set_expiry(900)

        step_data = request.session.get('step_data', {})

        required = [None, None, None, None, None, None, 'practice_area_category', 'practice_area', None, None, 'professional']

        are_available = set((r for r in required[:self.step] if r)).issubset(step_data)
        if not are_available:
            messages.error(request, 'Session timed out for your privacy. Please start again!')

        return are_available


def _serialize(obj):
    """
    Recursively clean data so it can be serialized via json.
    Data should be able to be fed back into the form that created
    it and get the original data back.
    """
    _serializers = {
        str: lambda obj: obj,
        int: lambda obj: obj,
        float: lambda obj: obj,
        list: lambda obj: [_serialize(x) for x in obj],
        dict: lambda obj: {k: _serialize(v) for k, v in obj.items()},
        datetime.date: lambda obj: obj.isoformat(),
        datetime.datetime: lambda obj: obj.isoformat(),
        Model: lambda obj: obj.id,
        PhoneNumber: lambda obj: obj.raw_input,
    }

    try:
        return _serializers[type(obj)](obj)
    except KeyError:
        for t, f in _serializers.items():
            if isinstance(obj, t):
                return f(obj)
        return obj
