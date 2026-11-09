from django.urls import reverse
from config import roles
from config.user_utils import c_user_group
from custom.models import Year
from notification.utils import notif_counts, notif_items

ROLE_NAME = dict(roles.ROLE_LABELS)


def _item(request, label, icon, name, args=(), names=(), match_kwargs=None):
	"""Satu entri menu. Aktif jika url_name saat ini termasuk `names` (dan kwargs cocok)."""
	url = reverse(name, args=args)
	match = request.resolver_match
	active = bool(match) and (match.url_name in (names or (name,)))
	if active and match_kwargs:
		active = all(str(match.kwargs.get(k)) == str(v) for k, v in match_kwargs.items())
	return {'label': label, 'icon': icon, 'url': url, 'active': active, 'children': []}


def _dropdown(label, icon, children):
	"""Menu induk dengan anak; aktif jika salah satu anak aktif."""
	return {'label': label, 'icon': icon, 'url': '#', 'children': children, 'active': any(c['active'] for c in children)}


def _menu(request, group):
	items = [_item(request, 'Varanda', 'fa-home', 'home')]
	if group == roles.ADMIN:
		items.append(_item(request, 'Painel', 'fa-tachometer', 'user-painel'))
		items.append(_item(request, 'Uzuáriu', 'fa-users', 'user-list', names=('user-list', 'user-add', 'user-update')))
		master = [_item(request, label, icon, 'master-list', args=(tipu,), names=('master-list', 'master-add', 'master-update'),
				match_kwargs={'tipu': tipu})
			for tipu, label, icon in [('suku', 'Suku', 'fa-map-marker'), ('aldeia', 'Aldeia', 'fa-map-o'),
				('organizasaun', 'Organizasaun', 'fa-flag'), ('ano', 'Tinan Ativu', 'fa-calendar')]]
		items.append(_dropdown('Data Master', 'fa-database', master))
		items.append(_item(request, 'Historia', 'fa-history', 'historia-list'))
		return items
	if group in roles.VIEW_ROLES:
		items.append(_item(request, 'Painel', 'fa-tachometer', 'membro-painel'))
		membru = [
			_item(request, 'Lista Membru', 'fa-list', 'membro-list', names=('membro-list', 'membro-detail', 'membro-update')),
			_item(request, 'Pesquiza', 'fa-search', 'membro-cari'),
		]
		if group in roles.INPUT_ROLES:
			membru.append(_item(request, 'Aumenta Membru', 'fa-user-plus', 'membro-add'))
		if group in roles.APROVA_ROLES:
			membru.append(_item(request, 'Hein Aprovasaun', 'fa-check-square-o', 'aprovasaun-list', names=('aprovasaun-list', 'aprovasaun-rejeita')))
		if group in roles.DUPLIKAT_ROLES:
			membru.append(_item(request, 'Dupla Potensial', 'fa-clone', 'membro-dupla'))
		items.append(_dropdown('Membru', 'fa-users', membru))
		items.append(_dropdown('Relatoriu', 'fa-list', [
			_item(request, 'Tabular', 'fa-table', 'report-dash'),
			_item(request, 'Grafiku', 'fa-bar-chart', 'report-chart')]))
		items.append(_item(request, 'Struktura', 'fa-sitemap', 'alokasaun-dash',
			names=('alokasaun-dash', 'alokasaun-list', 'alokasaun-add', 'alokasaun-update')))
		if group in roles.HISTORIA_ROLES:
			items.append(_item(request, 'Historia', 'fa-history', 'historia-list'))
	return items


def ano_ativu(request):
	context = {'ano_ativu': Year.objects.filter(is_active=True).first(), 'nav_items': [], 'nav_role': '', 'notif_items': [], 'notif_total': 0}
	if request.user.is_authenticated:
		group = c_user_group(request.user)
		context['nav_role'] = ROLE_NAME.get(group, '')
		context['nav_items'] = _menu(request, group)
		_, counts = notif_counts(request.user)
		context['notif_items'] = notif_items(group, counts)
		context['notif_total'] = counts['total']
	return context
