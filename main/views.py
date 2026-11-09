from urllib.parse import urlencode
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from config import roles
from config.user_utils import c_user_group, c_user_scope, membro_ativu
from custom.models import Village, Aldeia, Organizasaun, Year
from report.utils import matrix_rows

ROLE_NAME = dict(roles.ROLE_LABELS)

# Tabel dan grafik di Varanda mengikuti wilayah peran: (judul, parameter filter, field id, field nama)
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
HEAD = ['Total', 'Mane', 'Feto', 'Aprovadu', 'Pendente', 'Rejeitadu']


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


def _member_context(user, group):
	scope = c_user_scope(user)
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
	line1, line2 = _banner(group, scope)
	chart_name, chart_title = CHARTS[level]
	return {
		'kind': 'member', 'tot': tot, 'tables': tables, 'head': HEAD, 'banner': (line1, line2),
		'can_add': group in roles.INPUT_ROLES, 'can_aprova': group in roles.APROVA_ROLES,
		'chart_url': reverse(chart_name), 'chart_title': chart_title,
	}


def _admin_context():
	by_role = {r['groups__name']: r['n'] for r in User.objects.filter(is_active=True).values('groups__name').annotate(n=Count('id'))}
	return {
		'kind': 'admin', 'banner': ('ADMIN', 'SGDM-PDPADA'),
		'users_by_role': [(label, by_role.get(key, 0)) for key, label in roles.ROLE_LABELS],
		'master': [
			('Suku', Village.objects.count(), reverse('master-list', args=['suku'])),
			('Aldeia', Aldeia.objects.count(), reverse('master-list', args=['aldeia'])),
			('Organizasaun', Organizasaun.objects.filter(is_active=True).count(), reverse('master-list', args=['organizasaun'])),
			('Tinan', Year.objects.count(), reverse('master-list', args=['ano'])),
		],
		'users_total': sum(by_role.values()),
	}


@login_required
def home(request):
	group = c_user_group(request.user)
	context = {
		'group': group, 'title': 'Varanda', 'legend': 'Varanda',
		'meta_description': 'Varanda SGDM-PDPADA: rekapitulasaun membru Partido Democratico, Postu Dom Aleixo.',
	}
	if group == roles.ADMIN:
		context.update(_admin_context())
	elif group in roles.VIEW_ROLES:
		context.update(_member_context(request.user, group))
	else:
		context['kind'] = 'norole'
	return render(request, 'home/home.html', context)


def robots_txt(request):
	"""Sistem privat: larang semua mesin pencari."""
	return HttpResponse('User-agent: *\nDisallow: /\n', content_type='text/plain')


def error_403(request, exception=None):
	return render(request, 'home/403.html', status=403)


def error_404(request, exception=None):
	return render(request, 'home/404.html', status=404)


def error_500(request):
	return render(request, 'home/500.html', status=500)
