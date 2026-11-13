from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count
from django.urls import reverse
from custom.models import Village, Aldeia, Organizasaun, Year
from django.shortcuts import render, redirect, get_object_or_404
from config import roles
from config.decorators import allowed_users
from config.user_utils import c_user_group
from users.forms import UserForm

ROLE_NAME = dict(roles.ROLE_LABELS)


@login_required
@allowed_users(allowed_roles=[roles.ADMIN])
def UserList(request):
	group = c_user_group(request.user)
	users = User.objects.prefetch_related('groups').select_related('scope__village', 'scope__aldeia', 'scope__organizasaun').order_by('username')
	objects = []
	for u in users:
		role = u.groups.all()[0].name if u.groups.all() else None
		scope = getattr(u, 'scope', None)
		wilayah = (scope.aldeia or scope.village or scope.organizasaun) if scope else None
		objects.append({'obj': u, 'role': ROLE_NAME.get(role, role or '-'), 'wilayah': wilayah or '-'})
	context = {
		'group': group, 'objects': objects,
		'title': 'Lista Uzuáriu', 'legend': 'Lista Uzuáriu'
	}
	return render(request, 'users/list.html', context)


@login_required
@allowed_users(allowed_roles=[roles.ADMIN])
def UserAdd(request):
	group = c_user_group(request.user)
	if request.method == 'POST':
		form = UserForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, 'Uzuáriu foun aumenta ona.')
			return redirect('user-list')
	else:
		form = UserForm()
	context = {
		'form': form, 'group': group, 'cancel_url': '/users/',
		'back_url': 'user-list', 'back_label': 'Lista Uzuáriu',
		'title': 'Aumenta Uzuáriu', 'legend': 'Aumenta Uzuáriu'
	}
	return render(request, 'users/form.html', context)


@login_required
@allowed_users(allowed_roles=[roles.ADMIN])
def UserUpdate(request, pk):
	group = c_user_group(request.user)
	obj = get_object_or_404(User, pk=pk)
	if request.method == 'POST':
		form = UserForm(request.POST, instance=obj)
		if form.is_valid():
			if obj.pk == request.user.pk and (not form.cleaned_data['is_active'] or form.cleaned_data['group'] != roles.ADMIN):
				form.add_error(None, 'La bele desativa ka troka permisaun ba ita nia an rasik.')
			else:
				form.save()
				messages.success(request, 'Uzuáriu atualiza ona.')
				return redirect('user-list')
	else:
		form = UserForm(instance=obj)
	context = {
		'form': form, 'group': group, 'cancel_url': '/users/',
		'back_url': 'user-list', 'back_label': 'Lista Uzuáriu',
		'title': 'Edita Uzuáriu', 'legend': 'Edita Uzuáriu'
	}
	return render(request, 'users/form.html', context)


@login_required
@allowed_users(allowed_roles=[roles.ADMIN])
def UserPainel(request):
	"""Painel Admin: jumlah user aktif per peran dan ringkasan data master (tanpa data membru)."""
	group = c_user_group(request.user)
	by_role = {r['groups__name']: r['n'] for r in User.objects.filter(is_active=True).values('groups__name').annotate(n=Count('id'))}
	context = {
		'group': group, 'banner': ('ADMIN', 'SGDM-PDPADA'),
		'users_by_role': [(label, by_role.get(key, 0)) for key, label in roles.ROLE_LABELS],
		'users_total': sum(by_role.values()),
		'master': [
			('Suku', Village.objects.count(), reverse('master-list', args=['suku'])),
			('Aldeia', Aldeia.objects.count(), reverse('master-list', args=['aldeia'])),
			('Organizasaun', Organizasaun.objects.filter(is_active=True).count(), reverse('master-list', args=['organizasaun'])),
			('Tinan', Year.objects.count(), reverse('master-list', args=['ano'])),
		],
		'title': 'Painel Admin', 'legend': 'Painel Admin'
	}
	return render(request, 'users/painel.html', context)
