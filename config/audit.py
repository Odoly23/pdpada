import logging

from config.models import AuditLog

logger = logging.getLogger('pdpada.audit')


def client_ip(request):
    # axes jere ona IP proxy; ne'e de'it ba log. Uza REMOTE_ADDR (Whitenoise/Railway define husi proxy).
    fwd = request.META.get('HTTP_X_FORWARDED_FOR')
    return (fwd.split(',')[0].strip() if fwd else request.META.get('REMOTE_ADDR')) or None


def audit(request, action, target='', detail=''):
    user = getattr(request, 'user', None)
    user = user if user is not None and user.is_authenticated else None
    AuditLog.objects.create(
        user=user, username=user.get_username() if user else '',
        action=action, target=str(target)[:100], detail=detail, ip=client_ip(request),
    )
    logger.info('%s user=%s target=%s %s', action, user, target, detail)
