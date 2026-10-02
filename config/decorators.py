from functools import wraps

from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied

from config.scope import get_role


def allowed_users(allowed_roles=()):
    """Restrinji view ba papel espesífiku. Fallu = 403 (la 404 ka redirect)."""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if get_role(request.user) not in allowed_roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def perm_required(perm):
    """Login + Django permission; fallu = 403."""
    def decorator(view_func):
        return login_required(permission_required(perm, raise_exception=True)(view_func))
    return decorator
