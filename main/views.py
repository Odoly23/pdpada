from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render
from config import roles
from config.user_utils import c_user_group, membro_scope


def _counts(user):
	qs = membro_scope(user)
	return qs.aggregate(
		total=Count('id'),
		pendente=Count('id', filter=Q(aprovasaun='Pendente')),
		aprovadu=Count('id', filter=Q(aprovasaun='Aprovadu')),
		rejeitadu=Count('id', filter=Q(aprovasaun='Rejeitadu')),
	)


@login_required
def home(request):
	group = c_user_group(request.user)
	context = {
		'group': group,
		'counts': _counts(request.user) if group != roles.ADMIN and group else None,
		'title': 'Varanda', 'legend': 'Varanda'
	}
	return render(request, 'home/home.html', context)


def error_403(request, exception=None):
	return render(request, 'home/403.html', status=403)


def error_404(request, exception=None):
	return render(request, 'home/404.html', status=404)


def error_500(request):
	return render(request, 'home/500.html', status=500)
