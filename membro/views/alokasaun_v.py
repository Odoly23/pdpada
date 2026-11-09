from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from config import roles
from config.decorators import allowed_users
from config.user_utils import c_user_group, alokasaun_scope
from membro.forms import AlokasaunForm
from membro.models import Alokasaun
from membro.utils import log_historia


@login_required
@allowed_users(allowed_roles=roles.VIEW_ROLES)
def AlokasaunList(request):
	group = c_user_group(request.user)
	objects = alokasaun_scope(request.user).select_related('membro', 'village', 'aldeia', 'organizasaun')
	context = {
		'group': group, 'objects': objects, 'can_aloka': group in roles.ALOKA_ROLES,
		'title': 'Struktura no Pozisaun', 'legend': 'Struktura no Pozisaun'
	}
	return render(request, 'membro/alokasaun_list.html', context)


@login_required
@allowed_users(allowed_roles=roles.ALOKA_ROLES)
def AlokasaunAdd(request):
	group = c_user_group(request.user)
	if request.method == 'POST':
		form = AlokasaunForm(request.POST)
		if form.is_valid():
			instance = form.save(commit=False)
			instance.datetime = timezone.now()
			instance.user = request.user
			instance.save()
			log_historia(request.user, instance.membro, 'Aloka', f'{instance.pozisaun} {instance.nivel} {instance.unit() or ""}'.strip())
			messages.success(request, 'Pozisaun aloka ona.')
			return redirect('alokasaun-list')
	else:
		form = AlokasaunForm()
	context = {
		'form': form, 'group': group, 'cancel_url': '/membro/alokasaun/',
		'back_url': 'alokasaun-list', 'back_label': 'Struktura no Pozisaun',
		'title': 'Aloka Pozisaun', 'legend': 'Aloka Pozisaun'
	}
	return render(request, 'membro/alokasaun_form.html', context)


@login_required
@allowed_users(allowed_roles=roles.ALOKA_ROLES)
def AlokasaunUpdate(request, pk):
	group = c_user_group(request.user)
	obj = get_object_or_404(Alokasaun, pk=pk)
	if request.method == 'POST':
		form = AlokasaunForm(request.POST, instance=obj)
		if form.is_valid():
			instance = form.save(commit=False)
			instance.datetime = timezone.now()
			instance.user = request.user
			instance.save()
			log_historia(request.user, instance.membro, 'Edita Pozisaun',
				f'{instance.pozisaun} {instance.nivel} {instance.unit() or ""}, ativu: {instance.ativu}'.strip())
			messages.success(request, 'Pozisaun atualiza ona.')
			return redirect('alokasaun-list')
	else:
		form = AlokasaunForm(instance=obj)
	context = {
		'form': form, 'group': group, 'cancel_url': '/membro/alokasaun/',
		'back_url': 'alokasaun-list', 'back_label': 'Struktura no Pozisaun',
		'title': 'Edita Pozisaun', 'legend': 'Edita Pozisaun'
	}
	return render(request, 'membro/alokasaun_form.html', context)


@login_required
@allowed_users(allowed_roles=roles.ALOKA_ROLES)
@require_POST
def AlokasaunDel(request, pk):
	obj = get_object_or_404(Alokasaun, pk=pk)
	log_historia(request.user, obj.membro, 'Hamoos Pozisaun', f'{obj.pozisaun} {obj.nivel} {obj.unit() or ""}'.strip())
	obj.delete()
	messages.warning(request, 'Hamoos ho Susesu!.')
	return redirect('alokasaun-list')
