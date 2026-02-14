import re

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required


class RequireLoginMiddleware(object):
    """
        Middleware component that wraps the login_required decorator around matching URL patterns.
        Reference: https://stackoverflow.com/questions/2164069/best-way-to-make-djangos-login-required-the-default/46976284#46976284
    """

    def __init__(self, get_response):
         # One-time configuration and initialization.
        self.get_response = get_response

        self.required = tuple(re.compile(url) for url in settings.LOGIN_REQUIRED_URLS)
        self.exceptions = tuple(re.compile(url) for url in settings.LOGIN_REQUIRED_URLS_EXCEPTIONS)

    def __call__(self, request):

        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):

        # No need to process URLs if user already logged in
        if request.user.is_authenticated:
            return None

        # An exception match should immediately return None
        for url in self.exceptions:
            if url.match(request.path):
                return None

        # Requests matching a restricted URL pattern are returned
        # wrapped with the login_required decorator
        for url in self.required:
            if url.match(request.path):
                return login_required(view_func)(request, *view_args, **view_kwargs)

        # Explicitly return None for all non-matching requests
        return None


class RequireStaffAccessMiddleware(object):

    def __init__(self, get_response):
         # One-time configuration and initialization.
        self.get_response = get_response

        self.staff_access = tuple(re.compile(url) for url in settings.STAFF_LEVEL_ACCESS_REQUIRED_URLS)

    def __call__(self, request):

        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):

        # Requests matching a staff restricted URL pattern are returned
        # wrapped with the staff_member_required decorator
        for url in self.staff_access:
            if url.match(request.path):
                return staff_member_required(view_func)(request, *view_args, **view_kwargs)

        # Explicitly return None for all non-matching requests
        return None
