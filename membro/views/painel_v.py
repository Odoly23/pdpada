from urllib.parse import urlencode
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render
from django.urls import reverse
from config import roles
from config.decorators import allowed_users
from config.user_utils import c_user_group, c_user_scope, membro_ativu
from report.utils import matrix_rows

ROLE_NAME = dict(roles.ROLE_LABELS)

# Tabel dan grafik Painel mengikuti wilayah peran: (judul, parameter filter, field id, field nama)
TABLES = {
	'postu': [('Suku', 'village', 'village_id', 'village__name'), ('Organizasaun', 'organizasaun', 'organizasaun_id', 'organizasaun__code')],
	'suku': [('Aldeia', 'aldeia', 'aldeia_id', 'aldeia__name')],
	'aldeia': [('Organizasaun', 'organizasaun', 'organizasaun_id', 'organizasaun__code')],
	'org': [('Suku', 'village', 'village_id', 'village__name')],
}
CHARTS = {  # (nama url API, judul grafik)
	'postu': ('api-suku', 'Grafiku membru por suku'),
	'suku': ('api-aldeia', 'Grafiku membru por aldeia'),
	'aldeia': ('api-organizasaun', 'Grafiku membru por organizasaun'),
	'org': ('api-suku', 'Grafiku membru por suku'),
}


def _level(group):
	if group in roles.POSTU_ROLES:
		return 'postu'
	if group in roles.SUKU_ROLES:
		return 'suku'
	if group in roles.ALDEIA_ROLES:
		return 'aldeia'
	return 'org'


def _cells(row, key=None):
	"""Enam sel angka (nilai, tautan ke daftar membru terfilter)."""
	base = reverse('membro-list')

	def link(extra=None):
		params = {}
		if key:
			params[key] = row['id']
		if extra:
			params.update(extra)
		return base + ('?' + urlencode(params) if params else '')
	return [
		(row['total'], link()), (row['mane'], link({'sex': 'Mane'})), (row['feto'], link({'sex': 'Feto'})),
		(row['aprovadu'], link({'aprovasaun': 'Aprovadu'})), (row['pendente'], link({'aprovasaun': 'Pendente'})),
		(row['rejeitadu'], link({'aprovasaun': 'Rejeitadu'})),
	]


def _banner(group, scope):
	"""Dua baris judul banner: peran dan wilayahnya."""
	name = ROLE_NAME.get(group, '').upper()
	if group in roles.POSTU_ROLES:
		return name, 'POSTU DOM ALEIXO'
	if scope and group in roles.SUKU_ROLES and scope.village_id:
		return name, f'SUKU {scope.village.name.upper()}'
	if scope and group in roles.ALDEIA_ROLES and scope.aldeia_id:
		return name, f'ALDEIA {scope.aldeia.name.upper()} · SUKU {scope.aldeia.village.name.upper()}'
	if scope and group in roles.ORG_ROLES and scope.organizasaun_id:
		return name, f'ORGANIZASAUN {scope.organizasaun.code}'
	return name, 'SGDM-PDPADA'


@login_required
@allowed_users(allowed_roles=roles.VIEW_ROLES)
def PainelMembru(request):
	"""Painel membru: banner peran, tombol aksi, tabel matriks bertaut, dan grafik, sesuai wilayah peran."""
	user = request.user
	group = c_user_group(user)
	qs = membro_ativu(user)
	level = _level(group)
	tot = qs.aggregate(
		total=Count('id'), mane=Count('id', filter=Q(sex='Mane')), feto=Count('id', filter=Q(sex='Feto')),
		aprovadu=Count('id', filter=Q(aprovasaun='Aprovadu')), pendente=Count('id', filter=Q(aprovasaun='Pendente')),
		rejeitadu=Count('id', filter=Q(aprovasaun='Rejeitadu')))
	tables = []
	for title, key, id_field, name_field in TABLES[level]:
		rows = matrix_rows(qs, id_field, name_field)
		tables.append({
			'title': title, 'rows': [dict(r, cells=_cells(r, key)) for r in rows],
			'total_cells': _cells(dict(tot, id=0)),
		})
	chart_name, chart_title = CHARTS[level]
	context = {
		'group': group, 'tot': tot, 'tables': tables, 'banner': _banner(group, c_user_scope(user)),
		'can_add': group in roles.INPUT_ROLES, 'can_aprova': group in roles.APROVA_ROLES,
		'chart_url': reverse(chart_name), 'chart_title': chart_title,
		'title': 'Painel Membru', 'legend': 'Painel Membru',
		'meta_description': 'Painel membru Partido Democratico, Postu Dom Aleixo: total, sexu, aprovasaun por wilayah.',
	}
	return render(request, 'membro/painel.html', context)
