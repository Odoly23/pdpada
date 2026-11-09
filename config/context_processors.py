from django.urls import reverse
from config import roles
from config.user_utils import c_user_group
from custom.models import Year

ROLE_NAME = dict(roles.ROLE_LABELS)


def _item(request, label, icon, name, args=(), names=(), match_kwargs=None):
	"""Satu entri menu. Aktif jika url_name saat ini termasuk `names` (dan kwargs cocok)."""
	url = reverse(name, args=args)
	match = request.resolver_match
	active = bool(match) and (match.url_name in (names or (name,)))
	if active and match_kwargs:
		active = all(str(match.kwargs.get(k)) == str(v) for k, v in match_kwargs.items())
	return {'label': label, 'icon': icon, 'url': url, 'active': active, 'children': []}


def _menu(request, group):
	items = [_item(request, 'Varanda', 'fa-home', 'home')]
	if group == roles.ADMIN:
		items.append(_item(request, 'Uzuáriu', 'fa-users', 'user-list', names=('user-list', 'user-add', 'user-update')))
		master = {'label': 'Data Master', 'icon': 'fa-database', 'url': '#', 'active': False, 'children': []}
		for tipu, label, icon in [('suku', 'Suku', 'fa-map-marker'), ('aldeia', 'Aldeia', 'fa-map-o'),
				('organizasaun', 'Organizasaun', 'fa-flag'), ('ano', 'Tinan Ativu', 'fa-calendar')]:
			master['children'].append(_item(request, label, icon, 'master-list', args=(tipu,),
				names=('master-list', 'master-add', 'master-update'), match_kwargs={'tipu': tipu}))
		master['active'] = any(c['active'] for c in master['children'])
		items.append(master)
		items.append(_item(request, 'Historia', 'fa-history', 'historia-list'))
		return items
	if group in roles.VIEW_ROLES:
		items.append(_item(request, 'Rekap', 'fa-table', 'report-dash'))
		items.append(_item(request, 'Grafik', 'fa-bar-chart', 'report-chart'))
		items.append(_item(request, 'Membru', 'fa-list', 'membro-list', names=('membro-list', 'membro-detail', 'membro-update')))
		if group in roles.INPUT_ROLES:
			items.append(_item(request, 'Aumenta', 'fa-plus', 'membro-add'))
		if group in roles.APROVA_ROLES:
			items.append(_item(request, 'Aprovasaun', 'fa-check-square-o', 'aprovasaun-list', names=('aprovasaun-list', 'aprovasaun-rejeita')))
		items.append(_item(request, 'Struktura', 'fa-sitemap', 'alokasaun-list', names=('alokasaun-list', 'alokasaun-add', 'alokasaun-update')))
		if group in roles.HISTORIA_ROLES:
			items.append(_item(request, 'Historia', 'fa-history', 'historia-list'))
	return items


def ano_ativu(request):
	context = {'ano_ativu': Year.objects.filter(is_active=True).first(), 'nav_items': [], 'nav_role': ''}
	if request.user.is_authenticated:
		group = c_user_group(request.user)
		context['nav_role'] = ROLE_NAME.get(group, '')
		context['nav_items'] = _menu(request, group)
	return context
