from axes.signals import user_locked_out
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from config.models import AuditLog
from config.audit import client_ip


def _log(request, user, username, action, detail=''):
    AuditLog.objects.create(user=user, username=username[:150], action=action, detail=detail,
                            ip=client_ip(request) if request else None)


@receiver(user_logged_in)
def on_login(sender, request, user, **kw):
    _log(request, user, user.get_username(), 'login')


@receiver(user_logged_out)
def on_logout(sender, request, user, **kw):
    if user:
        _log(request, user, user.get_username(), 'logout')


@receiver(user_login_failed)
def on_login_failed(sender, credentials, request=None, **kw):
    _log(request, None, str(credentials.get('username', '')), 'login_failed')


@receiver(user_locked_out)
def on_locked_out(sender, request=None, username=None, **kw):
    _log(request, None, str(username or ''), 'locked_out', 'Limite tentativa login to’o.')
