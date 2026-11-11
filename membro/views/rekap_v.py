from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render
from django.urls import reverse
from config import roles
from config.decorators import allowed_users
from config.user_utils import c_user_group, membro_scope
from custom.models import Year, Village, Aldeia
from membro.models import Membro
from users.utils import c_user_emp

ROLE_NAME = dict(roles.ROLE_LABELS)
SEX_COUNTS = {'mane': Count('id', filter=Q(sex='Mane')), 'feto': Count('id', filter=Q(sex='Feto'))}


def _list_url(group, **params):
	"""Tautan ke lista membru terfilter; kosong untuk peran yang hanya boleh melihat rekapitulasi."""
	if group not in roles.LISTA_ROLES:
		return ''
	query = '&'.join(f'{k}={v}' for k, v in params.items())
	return reverse('membro-list') + ('?' + query if query else '')


@login_required
@allowed_users(allowed_roles=roles.POSTU_ROLES)
def VarandaPostu(request):
	"""Varanda Presidente/Coordenador/Sekretariu Postu: total, total por suku, kartu por aldeia, dan grafik. Hanya rekapitulasi."""
	group = c_user_group(request.user)
	e = c_user_emp(request.user)  # peran Postu tidak punya wilayah khusus; tetap dipakai agar pola view sama
	ano = Year.objects.filter(is_active=True).first()
	qs = membro_scope(request.user).filter(year=ano) if ano else membro_scope(request.user)
	total = qs.count()

	suku_count = dict(qs.order_by().values_list('village_id').annotate(n=Count('id')))
	objects1 = []
	for x in Village.objects.all():
		objects1.append([x, suku_count.get(x.pk, 0)])

	aldeia_count = {r['aldeia_id']: r for r in qs.order_by().values('aldeia_id').annotate(n=Count('id'), **SEX_COUNTS)}
	objects2 = []
	for x in Aldeia.objects.select_related('village'):
		row = aldeia_count.get(x.pk, {})
		objects2.append({
			'obj': x, 'n': row.get('n', 0), 'mane': row.get('mane', 0), 'feto': row.get('feto', 0),
			'url': _list_url(group, aldeia=x.pk),
		})
	chart = {'label': [f'{r["obj"].name}' for r in objects2], 'obj': [r['n'] for r in objects2]}

	context = {
		'group': group, 'role_label': ROLE_NAME.get(group, ''), 'e': e, 'total': total, 'total_url': _list_url(group),
		'objects1': objects1, 'objects2': objects2, 'chart': chart,
		'title': 'Varanda', 'legend': 'Varanda',
		'meta_description': 'Varanda SGDM-PDPADA: total membru, suku no aldeia Partido Democratico, Postu Dom Aleixo.',
	}
	return render(request, 'home/varanda_postu.html', context)


@login_required
@allowed_users(allowed_roles=roles.POSTU_ROLES)
def PainelPostu(request):
	"""Painel Postu: daftar TINAN | SUKU | grafik. Suku/tinan dipilih lewat tautan; hanya rekapitulasi."""
	group = c_user_group(request.user)
	years = list(Year.objects.order_by('-year'))
	ano_id = request.GET.get('ano', '')
	ano = next((y for y in years if str(y.pk) == ano_id), None) or next((y for y in years if y.is_active), None)
	qs = membro_scope(request.user)
	if ano:
		qs = qs.filter(year=ano)
	suku_id = request.GET.get('suku', '')
	suku_id = int(suku_id) if suku_id.isdigit() else 0

	year_count = dict(Membro.objects.order_by().values_list('year_id').annotate(n=Count('id')))
	objects1 = []
	for x in years:
		objects1.append([x, year_count.get(x.pk, 0), x.pk == (ano.pk if ano else 0)])

	suku_count = {r['village_id']: r for r in qs.order_by().values('village_id').annotate(n=Count('id'), **SEX_COUNTS)}
	objects2, selected = [], None
	for x in Village.objects.all():
		row = suku_count.get(x.pk, {})
		item = {'obj': x, 'n': row.get('n', 0), 'mane': row.get('mane', 0), 'feto': row.get('feto', 0), 'active': x.pk == suku_id}
		if item['active']:
			selected = item
		objects2.append(item)

	aldeias = []
	if selected:
		counts = dict(qs.filter(village_id=suku_id).order_by().values_list('aldeia_id').annotate(n=Count('id')))
		for x in Aldeia.objects.filter(village_id=suku_id):
			aldeias.append([x, counts.get(x.pk, 0), _list_url(group, aldeia=x.pk) if ano and ano.is_active else ''])

	chart = {'label': [r['obj'].name for r in objects2], 'obj': [r['n'] for r in objects2],
		'selected': next((i for i, r in enumerate(objects2) if r['active']), -1)}
	context = {
		'group': group, 'ano': ano, 'objects1': objects1, 'objects2': objects2, 'selected': selected, 'aldeias': aldeias,
		'chart': chart, 'total': sum(r['n'] for r in objects2),
		'selected_url': _list_url(group, village=suku_id) if selected and ano and ano.is_active else '',
		'title': 'Painel', 'legend': 'Painel',
		'meta_description': 'Painel SGDM-PDPADA: membru por tinan no suku, Partido Democratico, Postu Dom Aleixo.',
	}
	return render(request, 'membro/painel_postu.html', context)
