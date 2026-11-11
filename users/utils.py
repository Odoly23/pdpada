from users.models import UserScope


def c_user_scope(user):
	"""Profil wilayah/organisasi milik user (UserScope), atau "" jika belum ada. Padanan c_user_emp pada proyek lain."""
	objects = UserScope.objects.filter(user=user).select_related('village', 'aldeia', 'organizasaun').first()
	obj = ""
	if objects:
		obj = objects
	return obj


c_user_emp = c_user_scope  # nama yang sama dengan helper di proyek lain, agar pola view konsisten
