from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render
from config import roles
from config.decorators import allowed_users
from config.user_utils import c_user_group, membro_ativu


def _rows(qs, field, label_field, extra=()):
	"""Rekapitulasi membru per unit (suku/aldeia/organizasaun)."""
	return list(qs.values(field, label_field, *extra).annotate(
		total=Count('id'),
		mane=Count('id', filter=Q(sex='Mane')),
		feto=Count('id', filter=Q(sex='Feto')),
		aprovadu=Count('id', filter=Q(aprovasaun='Aprovadu')),
		pendente=Count('id', filter=Q(aprovasaun='Pendente')),
		rejeitadu=Count('id', filter=Q(aprovasaun='Rejeitadu')),
	).order_by(label_field))


@login_required
@allowed_users(allowed_roles=roles.VIEW_ROLES)
def Dash(request):
	group = c_user_group(request.user)
	qs = membro_ativu(request.user)
	context = {
		'group': group,
		'por_suku': _rows(qs, 'village_id', 'village__name'),
		'por_aldeia': _rows(qs.filter(), 'aldeia_id', 'aldeia__name', ('aldeia__village__name',)),
		'por_org': _rows(qs.filter(organizasaun__isnull=False), 'organizasaun_id', 'organizasaun__code'),
		'sem_org': qs.filter(organizasaun__isnull=True).count(),
		'title': 'Dashboard Membru', 'legend': 'Dashboard Membru'
	}
	return render(request, 'report/dash.html', context)
