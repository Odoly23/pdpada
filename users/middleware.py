from django.shortcuts import redirect
from django.urls import reverse


class ForcePasswordChangeMiddleware:
    """User foun/reset tenke troka password molok uza sistema."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated:
            profile = getattr(user, 'profile', None)
            if profile is not None and profile.must_change_password:
                allowed = {reverse('password_change'), reverse('logout')}
                if request.path not in allowed and not request.path.startswith('/static/'):
                    return redirect('password_change')
        return self.get_response(request)
