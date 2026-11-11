from django.contrib import messages
from django.http import FileResponse, Http404
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from config import roles
from config.decorators import allowed_users
from config.user_utils import c_user_group, membro_scope
from custom.models import Year, Village, Aldeia, Organizasaun
from membro.forms import MembroForm
from membro.models import Membro, Alokasaun
from membro.utils import snapshot, diff_snapshot, log_historia, membro_listing, aprovasaun_filters


@login_required
@allowed_users(allowed_roles=roles.LISTA_ROLES)
def MembroList(request):
	group = c_user_group(request.user)
	objects, semua_ano = membro_listing(request.user, request.GET)
	context = {
		'group': group, 'objects': objects, 'semua_ano': semua_ano,
		'can_add': group in roles.INPUT_ROLES, 'can_aprova': group in roles.APROVA_ROLES,
		'can_export': group in roles.EXPORT_ROLES,
		'filters': aprovasaun_filters(request.user, request.GET),
		'title': 'Lista Membru', 'legend': 'Lista Membru'
	}
	return render(request, 'membro/list.html', context)


@login_required
@allowed_users(allowed_roles=roles.LISTA_ROLES)
def MembroDetail(request, hashid):
	group = c_user_group(request.user)
	obj = get_object_or_404(membro_scope(request.user), hashed=hashid)
	alokasauns = Alokasaun.objects.filter(membro=obj, ativu='Sim').select_related('village', 'aldeia', 'organizasaun')
	historias = obj.historia.select_related('user')[:50] if group in roles.HISTORIA_ROLES else None
	context = {
		'group': group, 'obj': obj, 'hashid': hashid, 'alokasauns': alokasauns, 'historias': historias,
		'can_edit': group in roles.INPUT_ROLES,
		'can_aprova': group in roles.APROVA_ROLES and obj.aprovasaun == 'Pendente',
		'can_del': group in roles.APROVA_ROLES,
		'title': 'Detalha Membru', 'legend': 'Detalha Membru'
	}
	return render(request, 'membro/detail.html', context)


@login_required
@allowed_users(allowed_roles=roles.INPUT_ROLES)
def MembroAdd(request):
	group = c_user_group(request.user)
	ano = Year.objects.filter(is_active=True).first()
	if not ano:
		messages.error(request, 'Seidauk iha tinan ativu. Kontaktu Admin.')
		return redirect('membro-list')
	if request.method == 'POST':
		form = MembroForm(request.POST, request.FILES, user=request.user)
		if form.is_valid():
			instance = form.save(commit=False)
			instance.year = ano
			instance.aprovasaun = 'Pendente'
			instance.datetime = timezone.now()
			instance.user = request.user
			instance.save()
			log_historia(request.user, instance, 'Kria', f'Membru foun: {instance}')
			messages.success(request, 'Membru foun aumenta ona. Hein aprovasaun.')
			duplikadu = Membro.objects.filter(nome__iexact=instance.nome, date_of_birth=instance.date_of_birth).exclude(pk=instance.pk)
			if duplikadu.exists():
				messages.warning(request, f'Atensaun: iha membru seluk ho naran no data moris hanesan ({duplikadu.first()}). Verifika!')
			return redirect('membro-detail', instance.hashed)
	else:
		form = MembroForm(user=request.user)
	context = {
		'form': form, 'group': group, 'cancel_url': '/membro/',
		'back_url': 'membro-list', 'back_label': 'Lista Membru',
		'title': 'Aumenta Membru', 'legend': 'Aumenta Membru'
	}
	return render(request, 'membro/form.html', context)


@login_required
@allowed_users(allowed_roles=roles.INPUT_ROLES)
def MembroUpdate(request, hashid):
	group = c_user_group(request.user)
	obj = get_object_or_404(membro_scope(request.user), hashed=hashid)
	old = snapshot(obj)
	old_files = {'image': obj.image.name, 'file_eleitoral': obj.file_eleitoral.name}
	if request.method == 'POST':
		form = MembroForm(request.POST, request.FILES, instance=obj, user=request.user)
		if form.is_valid():
			if not form.has_changed():
				messages.info(request, 'Laiha mudansa.')
				return redirect('membro-detail', hashid)
			instance = form.save(commit=False)
			instance.aprovasaun = 'Pendente'
			instance.aprovadu_husi = None
			instance.data_aprovasaun = None
			instance.razaun_rejeita = None
			instance.datetime = timezone.now()
			instance.user = request.user
			instance.save()
			for name, old_name in old_files.items():  # file lama yang diganti dihapus dari penyimpanan
				if old_name and old_name != getattr(instance, name).name:
					Membro._meta.get_field(name).storage.delete(old_name)
			log_historia(request.user, instance, 'Edita', diff_snapshot(old, snapshot(instance)) or 'Fotu troka')
			messages.success(request, 'Data membru atualiza ona. Hein aprovasaun foun.')
			return redirect('membro-detail', hashid)
	else:
		form = MembroForm(instance=obj, user=request.user)
	context = {
		'form': form, 'group': group, 'hashid': hashid, 'cancel_url': f'/membro/{hashid}/',
		'back_url': 'membro-list', 'back_label': 'Lista Membru',
		'title': 'Edita Membru', 'legend': 'Edita Membru'
	}
	return render(request, 'membro/form.html', context)


@login_required
@allowed_users(allowed_roles=roles.APROVA_ROLES)
@require_POST
def MembroDel(request, hashid):
	obj = get_object_or_404(membro_scope(request.user), hashed=hashid)
	nome = str(obj)
	log_historia(request.user, None, 'Hamoos', f'Data membru hamoos: {nome}', nome=nome)
	if obj.image:
		obj.image.delete(save=False)
	if obj.file_eleitoral:
		obj.file_eleitoral.delete(save=False)
	obj.delete()
	messages.warning(request, 'Hamoos ho Susesu!.')
	return redirect('membro-list')


@login_required
@allowed_users(allowed_roles=roles.LISTA_ROLES)
def MembroFile(request, hashid, kind):
	"""Sajikan foto/PDF eleitoral dari penyimpanan privat, hanya untuk yang berhak melihat membru ini."""
	obj = get_object_or_404(membro_scope(request.user), hashed=hashid)
	if kind == 'foto':
		fieldfile, ctype, name = obj.image, 'image/jpeg', 'foto.jpg'
	elif kind == 'eleitoral':
		fieldfile, ctype, name = obj.file_eleitoral, 'application/pdf', 'kartaun-eleitoral.pdf'
	else:
		raise Http404
	if not fieldfile:
		raise Http404
	try:
		handle = fieldfile.storage.open(fieldfile.name, 'rb')
	except (FileNotFoundError, OSError):
		raise Http404
	if kind == 'eleitoral':
		log_historia(request.user, obj, 'Hare Dokumentu', 'Kartaun Eleitoral (PDF)')
	response = FileResponse(handle, content_type=ctype)
	response['Content-Disposition'] = f'inline; filename="{name}"'
	response['X-Content-Type-Options'] = 'nosniff'
	response['Cache-Control'] = 'private, no-store'
	return response
