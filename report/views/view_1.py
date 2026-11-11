import datetime
from urllib.parse import urlencode
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render
from django.urls import reverse
from config import roles
from config.decorators import allowed_users
from config.user_utils import c_user_group, membro_ativu
from membro.utils import AGE_BINS


def _url(**params):
	return reverse('membro-list') + '?' + urlencode(params)


def _count_rows(qs, field, key, label=None, none_label='Laiha', none_value=None, skip_none=False):
	"""Baris {name, total, url}: jumlah membru per nilai `field`, tautan ke daftar terfilter."""
	rows = []
	for r in qs.values(field).annotate(total=Count('id')).order_by(field):
		val = r[field]
		if val is None and skip_none:
			continue
		rows.append({
			'name': none_label if val is None else (label(val) if label else str(val)), 'total': r['total'],
			'url': _url(**{key: none_value if val is None else val}),
		})
	return rows


def _named_rows(qs, id_field, name_field, key, none_label='Laiha organizasaun'):
	rows = qs.values(id_field, name_field).annotate(total=Count('id')).order_by(name_field)
	return [{'name': r[name_field] or none_label, 'total': r['total'], 'url': _url(**{key: r[id_field] or 0})} for r in rows]


def _age_rows(qs):
	today = datetime.date.today()
	counts = {label: 0 for _, _, label in AGE_BINS}
	for dob in qs.values_list('date_of_birth', flat=True):
		age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
		for lo, hi, label in AGE_BINS:
			if lo <= age <= hi:
				counts[label] += 1
				break
	return [{'name': label, 'total': counts[label], 'url': _url(umur=label)} for _, _, label in AGE_BINS if counts[label]]


@login_required
@allowed_users(allowed_roles=roles.VIEW_ROLES)
def Dash(request):
	group = c_user_group(request.user)
	qs = membro_ativu(request.user)
	tot = qs.aggregate(
		total=Count('id'), mane=Count('id', filter=Q(sex='Mane')), feto=Count('id', filter=Q(sex='Feto')),
		pendente=Count('id', filter=Q(aprovasaun='Pendente')), aprovadu=Count('id', filter=Q(aprovasaun='Aprovadu')),
		rejeitadu=Count('id', filter=Q(aprovasaun='Rejeitadu')),
		ativu=Count('id', filter=Q(status='Ativu')), inativu=Count('id', filter=Q(status='Inativu')),
		falesidu=Count('id', filter=Q(status='Falesidu')),
		sem_org=Count('id', filter=Q(organizasaun__isnull=True)))
	age = _age_rows(qs)
	tables = [
		{'title': 'Membru Tuir Suku', 'head': 'Suku', 'rows': _named_rows(qs, 'village_id', 'village__name', 'village')},
		{'title': 'Membru Tuir Aldeia', 'head': 'Aldeia', 'rows': _named_rows(qs, 'aldeia_id', 'aldeia__name', 'aldeia')},
		{'title': 'Membru Tuir Organizasaun', 'head': 'Organizasaun', 'rows': _named_rows(qs, 'organizasaun_id', 'organizasaun__code', 'organizasaun')},
		{'title': 'Membru Tuir Tinan Tama', 'head': 'Tinan', 'rows': _count_rows(qs, 'data_hakbit__year', 'hakbit', skip_none=True)},
		{'title': 'Membru Tuir Idade', 'head': 'Idade', 'rows': age},
		{'title': 'Membru Tuir Estado Civil', 'head': 'Estado Civil', 'rows': _count_rows(qs, 'marital', 'marital', none_label='Laiha', none_value='laiha')},
	]
	context = {
		'group': group, 'tot': tot, 'tables': tables, 'can_link': group in roles.LISTA_ROLES,
		'can_add': group in roles.INPUT_ROLES, 'can_aprova': group in roles.APROVA_ROLES,
		'title': 'Relatoriu Tabular', 'legend': 'Relatoriu Tabular',
		'meta_description': 'Relatoriu tabular membru Partido Democratico, Postu Dom Aleixo.',
	}
	return render(request, 'report/dash.html', context)


@login_required
@allowed_users(allowed_roles=roles.VIEW_ROLES)
def ChartDash(request):
	context = {
		'group': c_user_group(request.user),
		'title': 'Relatoriu Grafiku', 'legend': 'Relatoriu Grafiku',
		'meta_description': 'Relatoriu grafiku membru Partido Democratico, Postu Dom Aleixo.',
	}
	return render(request, 'report/chart_dash.html', context)
