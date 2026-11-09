from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from config import roles
from config.decorators import allowed_users
from config.user_utils import c_user_group, membro_scope
from membro.forms import RejeitaForm
from membro.models import Membro
from membro.utils import log_historia


def _aprova(user, obj):
	obj.aprovasaun = 'Aprovadu'
	obj.aprovadu_husi = user
	obj.data_aprovasaun = timezone.now()
	obj.razaun_rejeita = None
	obj.save()
	log_historia(user, obj, 'Aprova', f'Aprovadu husi {user.get_username()}')


@login_required
@allowed_users(allowed_roles=roles.APROVA_ROLES)
def AprovasaunList(request):
	group = c_user_group(request.user)
	objects = membro_scope(request.user).filter(aprovasaun='Pendente').select_related('village', 'aldeia', 'organizasaun')
	context = {
		'group': group, 'objects': objects,
		'title': 'Hein Aprovasaun', 'legend': 'Membru Hein Aprovasaun'
	}
	return render(request, 'membro/aprovasaun_list.html', context)


@login_required
@allowed_users(allowed_roles=roles.APROVA_ROLES)
@require_POST
def AprovasaunAprova(request, hashid):
	obj = get_object_or_404(membro_scope(request.user), hashed=hashid)
	if obj.aprovasaun != 'Pendente':
		messages.info(request, 'Data ne\'e la iha estatutu Pendente.')
	else:
		_aprova(request.user, obj)
		messages.success(request, f'{obj.nome} aprovadu ona.')
	if request.POST.get('next') == 'detail':
		return redirect('membro-detail', hashid)
	return redirect('aprovasaun-list')


@login_required
@allowed_users(allowed_roles=roles.APROVA_ROLES)
@require_POST
def AprovasaunBulk(request):
	hashes = request.POST.getlist('hashid')
	objs = membro_scope(request.user).filter(hashed__in=hashes, aprovasaun='Pendente')
	total = 0
	for obj in objs:
		_aprova(request.user, obj)
		total += 1
	if total:
		messages.success(request, f'{total} membru aprovadu ona.')
	else:
		messages.info(request, 'Laiha membru ne\'ebé hili.')
	return redirect('aprovasaun-list')


@login_required
@allowed_users(allowed_roles=roles.APROVA_ROLES)
def AprovasaunRejeita(request, hashid):
	group = c_user_group(request.user)
	obj = get_object_or_404(membro_scope(request.user), hashed=hashid, aprovasaun='Pendente')
	if request.method == 'POST':
		form = RejeitaForm(request.POST)
		if form.is_valid():
			obj.aprovasaun = 'Rejeitadu'
			obj.aprovadu_husi = request.user
			obj.data_aprovasaun = timezone.now()
			obj.razaun_rejeita = form.cleaned_data['razaun']
			obj.save()
			log_historia(request.user, obj, 'Rejeita', f'Razaun: {obj.razaun_rejeita}')
			messages.warning(request, f'{obj.nome} rejeitadu.')
			return redirect('aprovasaun-list')
	else:
		form = RejeitaForm()
	context = {
		'form': form, 'group': group, 'obj': obj, 'cancel_url': '/membro/aprovasaun/',
		'back_url': 'aprovasaun-list', 'back_label': 'Hein Aprovasaun',
		'title': 'Rejeita Membru', 'legend': f'Rejeita: {obj.nome}'
	}
	return render(request, 'membro/form.html', context)
