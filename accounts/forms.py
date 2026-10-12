from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from core.models import AuditLog


def _key(username, ip):
    return f"loginfail:{username.lower()}:{ip}"


def client_ip(request):
    return request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR", "")


class LockoutAuthenticationForm(AuthenticationForm):
    """Login form that locks an account/IP pair after LOGIN_MAX_ATTEMPTS failures."""

    def clean(self):
        username = self.cleaned_data.get("username", "")
        key = _key(username, client_ip(self.request))
        if cache.get(key, 0) >= settings.LOGIN_MAX_ATTEMPTS:
            AuditLog.record("login_locked", request=self.request, username=username)
            raise ValidationError(
                _("Tentativa barak liu. Hein minutu %(m)d ho tenta fali.") % {"m": settings.LOGIN_LOCKOUT_SECONDS // 60},
                code="locked",
            )
        try:
            result = super().clean()
        except ValidationError:
            cache.set(key, cache.get(key, 0) + 1, settings.LOGIN_LOCKOUT_SECONDS)
            AuditLog.record("login_failed", request=self.request, username=username)
            raise
        cache.delete(key)
        return result
