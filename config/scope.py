"""
Helper tunggal ba papel (role) no eskopu (wilayah/organizasaun).

Tuir audit: la uza `user.groups.all()[0]` (la determinístiku). Uza `get_role()`.
SEMPRE filtra queryset liu husi `membru_queryset(user)` — nunca `Membru.objects.all()`.
"""
from config import roles as R


def get_role(user):
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return R.ADMIN
    cached = getattr(user, '_role', '__unset__')
    if cached != '__unset__':
        return cached
    names = set(user.groups.values_list('name', flat=True))
    role = next((r for r in R.ROLE_PRIORITY if r in names), None)
    user._role = role
    return role


def get_profile(user):
    try:
        return user.profile
    except Exception:  # RelatedObjectDoesNotExist
        return None


def scope_label(user):
    """Naran eskopu ba header (Aldeia X / Suku Y / ...)."""
    role, p = get_role(user), get_profile(user)
    if role in R.GLOBAL_ROLES:
        return 'Nasional'
    if not p:
        return ''
    if role == R.POSTU and p.postu_id:
        return f'Postu {p.postu}'
    if role == R.SUKU and p.village_id:
        return f'Suku {p.village}'
    if role == R.ALDEIA and p.aldeia_id:
        return f'Aldeia {p.aldeia}'
    if role in R.ORG_ROLES and p.organizasaun_id:
        return str(p.organizasaun)
    return ''


def membru_queryset(user):
    """Membru ne'ebé user ne'e MAK BELE HARE (la inklui ne'ebé hamoos ona)."""
    from membro.models import Membru
    qs = Membru.objects.all()  # ActiveManager: la inklui soft-deleted
    role, p = get_role(user), get_profile(user)
    if role in R.GLOBAL_ROLES:
        return qs
    if not role or not p:
        return qs.none()
    if role == R.POSTU and p.postu_id:
        return qs.filter(aldeia__village__administrativepost_id=p.postu_id)
    if role == R.SUKU and p.village_id:
        return qs.filter(aldeia__village_id=p.village_id)
    if role == R.ALDEIA and p.aldeia_id:
        return qs.filter(aldeia_id=p.aldeia_id)
    if role in R.ORG_ROLES and p.organizasaun_id:
        return qs.filter(organizasaun=p.organizasaun_id)
    return qs.none()


def kargu_queryset(user):
    """Kargu (Coordenador/Sekjen) ne'ebé user bele haree, tuir eskopu."""
    from django.db.models import Q
    from membro.models import Kargu
    qs = Kargu.objects.select_related('membru', 'postu', 'village', 'aldeia')
    role, p = get_role(user), get_profile(user)
    if role in R.GLOBAL_ROLES:
        return qs
    if not role or not p:
        return qs.none()
    if role == R.POSTU and p.postu_id:
        return qs.filter(Q(postu_id=p.postu_id) | Q(village__administrativepost_id=p.postu_id) |
                         Q(aldeia__village__administrativepost_id=p.postu_id))
    if role == R.SUKU and p.village_id:
        return qs.filter(Q(village_id=p.village_id) | Q(aldeia__village_id=p.village_id))
    if role == R.ALDEIA and p.aldeia_id:
        return qs.filter(aldeia_id=p.aldeia_id)
    return qs.none()
