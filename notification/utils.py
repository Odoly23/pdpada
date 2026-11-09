from django.urls import reverse
from config import roles
from config.user_utils import c_user_group, membro_scope


def notif_counts(user):
	"""Jumlah notifikasi sesuai peran: approver = membru Pendente, sekjer = membru Rejeitadu (perlu diperbaiki)."""
	group = c_user_group(user)
	counts = {'pendente': 0, 'rejeitadu': 0}
	if group in roles.APROVA_ROLES:
		counts['pendente'] = membro_scope(user).filter(aprovasaun='Pendente').count()
	if group in roles.INPUT_ROLES:
		counts['rejeitadu'] = membro_scope(user).filter(aprovasaun='Rejeitadu').count()
	counts['total'] = counts['pendente'] + counts['rejeitadu']
	return group, counts


def notif_items(group, counts):
	items = []
	if group in roles.APROVA_ROLES:
		items.append({'key': 'pendente', 'label': 'Membru Hein Aprovasaun', 'url': reverse('aprovasaun-list'), 'count': counts['pendente']})
	if group in roles.INPUT_ROLES:
		items.append({'key': 'rejeitadu', 'label': 'Membru Rejeitadu (presiza koriji)',
			'url': reverse('membro-list') + '?aprovasaun=Rejeitadu&ano=hotu', 'count': counts['rejeitadu']})
	return items
