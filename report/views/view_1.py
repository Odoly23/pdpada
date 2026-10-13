from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render
from config import roles
from config.decorators import allowed_users
from config.user_utils import c_user_group, membro_ativu


def _rows(qs, id_field, name_field):
	"""Rekap jumlah membru per unit sebagai daftar {id, name, total}."""
	rows = qs.values(id_field, name_field).annotate(total=Count('id')).order_by(name_field)
	return [{'id': r[id_field], 'name': r[name_field], 'total': r['total']} for r in rows]


@login_required
@allowed_users(allowed_roles=roles.VIEW_ROLES)
def Dash(request):
	group = c_user_group(request.user)
	qs = membro_ativu(request.user)
	tot = qs.aggregate(
		total=Count('id'),
		mane=Count('id', filter=Q(sex='Mane')),
		feto=Count('id', filter=Q(sex='Feto')),
		pendente=Count('id', filter=Q(aprovasaun='Pendente')),
		aprovadu=Count('id', filter=Q(aprovasaun='Aprovadu')),
		rejeitadu=Count('id', filter=Q(aprovasaun='Rejeitadu')),
		sem_org=Count('id', filter=Q(organizasaun__isnull=True)),
	)
	context = {
		'group': group, 'tot': tot,
		'por_org': _rows(qs.filter(organizasaun__isnull=False), 'organizasaun_id', 'organizasaun__code'),
		'por_suku': _rows(qs, 'village_id', 'village__name'),
		'por_aldeia': _rows(qs, 'aldeia_id', 'aldeia__name'),
		'por_status': _rows(qs, 'status', 'status'),
		'por_tinan': _rows(qs.filter(data_hakbit__isnull=False), 'data_hakbit__year', 'data_hakbit__year'),
		'title': 'Dashboard Membru', 'legend': 'Dashboard Membru'
	}
	return render(request, 'report/dash.html', context)


@login_required
@allowed_users(allowed_roles=roles.VIEW_ROLES)
def ChartDash(request):
	context = {
		'group': c_user_group(request.user),
		'title': 'Grafik Membru', 'legend': 'Grafik Membru'
	}
	return render(request, 'report/chart_dash.html', context)
