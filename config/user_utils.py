from config import roles


def c_user_group(user):
	if not user.is_authenticated:
		return None
	group = user.groups.all()[:1]
	return group[0].name if group else None


def c_user_scope(user):
	from users.models import UserScope
	return UserScope.objects.filter(user=user).select_related('village', 'aldeia', 'organizasaun').first()


def membro_scope(user, qs=None):
	"""Queryset Membro yang boleh dilihat user sesuai peran dan wilayahnya."""
	from membro.models import Membro
	qs = Membro.objects.all() if qs is None else qs
	group = c_user_group(user)
	if group in roles.POSTU_ROLES:
		return qs
	scope = c_user_scope(user)
	if scope:
		if group in roles.SUKU_ROLES and scope.village_id:
			return qs.filter(village_id=scope.village_id)
		if group in roles.ALDEIA_ROLES and scope.aldeia_id:
			return qs.filter(aldeia_id=scope.aldeia_id)
		if group in roles.ORG_ROLES and scope.organizasaun_id:
			return qs.filter(organizasaun_id=scope.organizasaun_id)
	return qs.none()


def alokasaun_scope(user, qs=None):
	from membro.models import Alokasaun
	qs = Alokasaun.objects.all() if qs is None else qs
	group = c_user_group(user)
	if group in roles.POSTU_ROLES:
		return qs
	scope = c_user_scope(user)
	if scope:
		if group in roles.SUKU_ROLES and scope.village_id:
			return qs.filter(nivel='Suku', village_id=scope.village_id) | qs.filter(nivel='Aldeia', aldeia__village_id=scope.village_id)
		if group in roles.ALDEIA_ROLES and scope.aldeia_id:
			return qs.filter(nivel='Aldeia', aldeia_id=scope.aldeia_id)
		if group in roles.ORG_ROLES and scope.organizasaun_id:
			return qs.filter(nivel='Organizasaun', organizasaun_id=scope.organizasaun_id)
	return qs.none()


def membro_ativu(user):
	"""membro_scope yang dibatasi pada tinan ativu (dipakai laporan dan API)."""
	from custom.models import Year
	qs = membro_scope(user)
	ano = Year.objects.filter(is_active=True).first()
	return qs.filter(year=ano) if ano else qs
