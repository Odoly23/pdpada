from config import roles as R
from config.scope import get_role, scope_label


def rbac(request):
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return {}
    role = get_role(user)
    return {'role': role, 'role_label': R.ROLE_LABELS.get(role, ''), 'scope_label': scope_label(user)}
