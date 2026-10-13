from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from config import roles
from config.decorators import allowed_users
from config.user_utils import c_user_group
from membro.models import Historia

LIMITE = 3000


@login_required
@allowed_users(allowed_roles=roles.HISTORIA_ROLES)
def HistoriaList(request):
	group = c_user_group(request.user)
	objects = Historia.objects.select_related('user', 'membro')
	aksaun = request.GET.get('aksaun')
	if aksaun:
		objects = objects.filter(aksaun=aksaun)
	context = {
		'group': group, 'objects': objects[:LIMITE], 'limite': LIMITE,
		'aksauns': Historia.objects.order_by().values_list('aksaun', flat=True).distinct(),
		'title': 'Historia Mudansa Data', 'legend': 'Historia Mudansa Data'
	}
	return render(request, 'membro/historia_list.html', context)
