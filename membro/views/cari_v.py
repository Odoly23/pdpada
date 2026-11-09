from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from config import roles
from config.decorators import allowed_users
from config.user_utils import c_user_group
from membro.utils import search_membro, SEARCH_MIN


@login_required
@allowed_users(allowed_roles=roles.VIEW_ROLES)
def MembroCari(request):
	"""Pencarian cepat membru (naran, Nu. Eleitoral, Nu. Telemovel) dalam wilayah user."""
	group = c_user_group(request.user)
	q = ' '.join(request.GET.get('q', '').split())
	objects = search_membro(request.user, q) if q else []
	context = {
		'group': group, 'q': q, 'objects': objects, 'min_chars': SEARCH_MIN,
		'too_short': bool(q) and len(q) < SEARCH_MIN,
		'title': 'Pesquiza Membru', 'legend': 'Pesquiza Membru'
	}
	return render(request, 'membro/cari.html', context)
