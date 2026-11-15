from django.contrib import messages
from django.http import FileResponse, Http404
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from config import roles
from config.decorators import allowed_users
from config.user_utils import c_user_group, c_user_scope, membro_scope
from custom.models import Year, Village, Aldeia, Organizasaun
from django.urls import reverse
from membro.forms import MembroForm, KontaktuForm, ServisuForm, EdukasaunForm, AlokasaunMembroForm
from membro.models import Membro, Alokasaun, Servisu, Edukasaun
from membro.utils import snapshot, diff_snapshot, log_historia, membro_listing, aprovasaun_filters, kategoria_filters, SERVISU_BUTTONS


# lista membru (filtru kategoria, servisu, suku, aldeia)
@login_required
@allowed_users(allowed_roles=roles.DETALLE_ROLES)
def MembroList(request):
	group = c_user_group(request.user)
	objects, semua_ano = membro_listing(request.user, request.GET)
	context = {
		'group': group, 'objects': objects, 'semua_ano': semua_ano,
		'can_add': group in roles.INPUT_ROLES, 'can_aprova': group in roles.APROVA_ROLES,
		'can_export': group in roles.EXPORT_ROLES,
		'filters': aprovasaun_filters(request.user, request.GET),
		'jenis_filters': kategoria_filters(request.user, request.GET),
		'servisu_filters': kategoria_filters(request.user, request.GET, 'servisu', SERVISU_BUTTONS),
		'title': 'Lista Membru', 'legend': 'Lista Membru'
	}
	return render(request, 'membro/list.html', context)


# detalle membru (dadus, kontaktu, servisu)
@login_required
@allowed_users(allowed_roles=roles.DETALLE_ROLES)
def MembroDetail(request, hashid):
	group = c_user_group(request.user)
	obj = get_object_or_404(membro_scope(request.user), hashed=hashid)
	alokasauns = Alokasaun.objects.filter(membro=obj, ativu='Sim').select_related('village', 'aldeia', 'organizasaun')
	historias = obj.historia.select_related('user')[:50] if group in roles.HISTORIA_ROLES else None
	context = {
		'group': group, 'obj': obj, 'hashid': hashid, 'alokasauns': alokasauns, 'historias': historias,
		'servisu': Servisu.objects.filter(membro=obj).select_related('municipality').first(),
		'edukasaun': Edukasaun.objects.filter(membro=obj).first(),
		'can_aloka': _bele_aloka(request.user, obj),
		'can_edit': group in roles.INPUT_ROLES,
		'can_aprova': group in roles.APROVA_ROLES and obj.aprovasaun == 'Pendente',
		'can_del': group in roles.APROVA_ROLES,
		'title': 'Detalha Membru', 'legend': 'Detalha Membru'
	}
	return render(request, 'membro/detail.html', context)


# adisiona dadus membru
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
			scope = c_user_scope(request.user)
			if group == roles.SEKR_ORG and scope and scope.organizasaun_id:
				instance.organizasaun_id = scope.organizasaun_id  # sekjer organizasaun: membru tama organizasaun nia
			instance.aprovasaun = 'Pendente'
			instance.datetime = timezone.now()
			instance.user = request.user
			instance.save()
			log_historia(request.user, instance, 'Kria', f'Membru foun ({instance.kategoria}): {instance}')
			messages.success(request, 'Membru foun aumenta ona. Hein aprovasaun. Lanjuta: hatama edukasaun, servisu no pozisaun.')
			duplikadu = Membro.objects.filter(nome__iexact=instance.nome, date_of_birth=instance.date_of_birth).exclude(pk=instance.pk)
			if duplikadu.exists():
				messages.warning(request, f'Atensaun: iha membru seluk ho naran no data moris hanesan ({duplikadu.first()}). Verifika!')
			return redirect(reverse('membro-edukasaun', args=[instance.hashed]) + '?fluxu=1')  # pasu tuir mai: edukasaun
	else:
		form = MembroForm(user=request.user)
	context = {
		'form': form, 'group': group, 'cancel_url': '/membro/',
		'back_url': 'membro-list', 'back_label': 'Lista Membru',
		'title': 'Aumenta Membru', 'legend': 'Aumenta Membru'
	}
	return render(request, 'membro/form.html', context)


# hadia/edita dadus membru
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


# hamoos membru
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


# hatudu foto/PDF membru (privadu)
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


# fluxu input membru: membru -> edukasaun -> servisu -> pozisaun -> detalle
def _bele_aloka(user, emp):
	"""Pasu pozisaun (Militante/Simpatizante/Ejekutivu) ba membru ativu, seidauk iha pozisaun no la rejeitadu; input hotu uluk, depois aprova."""
	return (c_user_group(user) in roles.INPUT_ROLES + roles.ALOKA_ROLES and emp.aprovasaun != 'Rejeitadu' and emp.status == 'Ativu' and not emp.is_colocado)


# URL pasu tuir mai iha fluxu (ho ?fluxu=1)
def _url_tuir_mai(request, emp, pasu):
	if pasu == 'edukasaun':
		return reverse('membro-servisu', args=[emp.hashed]) + '?fluxu=1'
	if pasu == 'servisu' and _bele_aloka(request.user, emp):
		return reverse('membro-aloka', args=[emp.hashed]) + '?fluxu=1'
	return reverse('membro-detail', args=[emp.hashed])


# depois rai: ba pasu tuir mai (se fluxu) ka detalle
def _pasu_tuir_mai(request, emp, pasu):
	if request.GET.get('fluxu') == '1':
		return redirect(_url_tuir_mai(request, emp, pasu))
	return redirect('membro-detail', hashid=emp.hashed)


# kontestu formuláriu fluxu (botaun "Liu pasu ne'e" no informasaun pasu)
def _fluxu_context(request, emp, pasu, info):
	if request.GET.get('fluxu') != '1':
		return {}
	return {'skip_url': _url_tuir_mai(request, emp, pasu), 'fluxu_info': info}


# hadia/edita edukasaun membru (nivel as-aas)
@login_required
@allowed_users(allowed_roles=roles.INPUT_ROLES)
def EdukasaunUpdate(request, hashid):
	group = c_user_group(request.user)
	emp = get_object_or_404(membro_scope(request.user), hashed=hashid)
	objects = Edukasaun.objects.filter(membro=emp).first()
	old = objects.resumu() if objects else '-'
	if request.method == 'POST':
		form = EdukasaunForm(request.POST, instance=objects)
		if form.is_valid():
			instance = form.save(commit=False)
			instance.membro = emp
			instance.save()
			log_historia(request.user, emp, 'Edita Edukasaun', f'Edukasaun: {old} -> {instance.resumu()}')
			messages.success(request, 'Dadus edukasaun rai ona.')
			return _pasu_tuir_mai(request, emp, 'edukasaun')
	else:
		form = EdukasaunForm(instance=objects)
	context = {
		'form': form, 'group': group, 'hashid': hashid, 'emp': emp, 'cancel_url': f'/membro/{hashid}/',
		'back_url': 'membro-detail', 'back_args': [hashid], 'back_label': 'Detalha Membru',
		'title': 'Edukasaun Membru', 'legend': f'Edukasaun · {emp.nome}', **_fluxu_context(request, emp, 'edukasaun', 'Pasu 1 husi 3: nivel edukasaun.')
	}
	return render(request, 'main/form.html', context)


# pasu pozisaun: hili Militante, Simpatizante ka Ejekutivu (nivel Suku, Aldeia ka Organizasaun; Postu deit Admin)
@login_required
@allowed_users(allowed_roles=roles.INPUT_ROLES + roles.ALOKA_ROLES)
def MembroAloka(request, hashid):
	group = c_user_group(request.user)
	emp = get_object_or_404(membro_scope(request.user), hashed=hashid)
	if not _bele_aloka(request.user, emp):
		messages.warning(request, 'Membru ne\'e la bele troka kategoria/pozisaun (rejeitadu, la ativu ka iha ona pozisaun).')
		return redirect('membro-detail', hashid=hashid)
	if request.method == 'POST':
		form = AlokasaunMembroForm(request.POST, membro=emp, user=request.user)
		if form.is_valid():
			tipu = form.cleaned_data['tipu']
			kategoria = 'Simpatizante' if tipu == 'Simpatizante' else 'Militante'
			if emp.kategoria != kategoria:
				old = emp.kategoria
				Membro.objects.filter(pk=emp.pk).update(kategoria=kategoria)
				log_historia(request.user, emp, 'Edita Kategoria', f'Kategoria: {old} -> {kategoria}')
			if tipu == 'Ejekutivu':
				instance = form.save(commit=False)
				instance.datetime = timezone.now()
				instance.user = request.user
				instance.save()
				log_historia(request.user, emp, 'Aloka', f'{instance.pozisaun} {instance.nivel} {instance.unit() or ""}'.strip())
				messages.success(request, 'Pozisaun aloka ona. Hein aprovasaun.')
			else:
				messages.success(request, f'{emp.nome} rai ona nu\'udar {tipu}. Hein aprovasaun.')
			return redirect('membro-detail', hashid=hashid)
	else:
		form = AlokasaunMembroForm(membro=emp, user=request.user, initial={'membro': emp.pk})
	context = {
		'form': form, 'group': group, 'hashid': hashid, 'emp': emp, 'cancel_url': f'/membro/{hashid}/',
		'back_url': 'membro-detail', 'back_args': [hashid], 'back_label': 'Detalha Membru',
		'title': 'Kategoria no Pozisaun', 'legend': f'Kategoria no Pozisaun · {emp.nome}',
		'fluxu_info': 'Pasu 3 husi 3: hili Militante, Simpatizante ka Ejekutivu.' if request.GET.get('fluxu') == '1' else ''
	}
	return render(request, 'membro/alokasaun_form.html', context)


# hadia/edita kontaktu membru (telefone no hela fatin)
@login_required
@allowed_users(allowed_roles=roles.INPUT_ROLES)
def KontaktuUpdate(request, hashid):
	group = c_user_group(request.user)
	emp = get_object_or_404(membro_scope(request.user), hashed=hashid)
	old = f'{emp.telefone or "-"} / {emp.address or "-"}'
	if request.method == 'POST':
		form = KontaktuForm(request.POST, instance=emp)
		if form.is_valid():
			instance = form.save()
			log_historia(request.user, instance, 'Edita Kontaktu', f'Kontaktu: {old} -> {instance.telefone or "-"} / {instance.address or "-"}')
			messages.success(request, 'Informasaun kontaktu altera ona.')
			return redirect('membro-detail', hashid=hashid)
	else:
		form = KontaktuForm(instance=emp)
	context = {
		'form': form, 'group': group, 'hashid': hashid, 'emp': emp, 'cancel_url': f'/membro/{hashid}/',
		'back_url': 'membro-detail', 'back_args': [hashid], 'back_label': 'Detalha Membru',
		'title': 'Altera Kontaktu', 'legend': f'Kontaktu · {emp.nome}'
	}
	return render(request, 'main/form.html', context)


# adisiona ka hadia dadus servisu membru (iha servisu governu/laos governu ka seidauk servisu)
@login_required
@allowed_users(allowed_roles=roles.INPUT_ROLES)
def ServisuUpdate(request, hashid):
	group = c_user_group(request.user)
	emp = get_object_or_404(membro_scope(request.user), hashed=hashid)
	objects = Servisu.objects.filter(membro=emp).first()
	old = objects.resumu() if objects else '-'
	if request.method == 'POST':
		form = ServisuForm(request.POST, instance=objects)
		if form.is_valid():
			instance = form.save(commit=False)
			instance.membro = emp
			instance.save()
			log_historia(request.user, emp, 'Edita Servisu', f'Servisu: {old} -> {instance.resumu()}')
			messages.success(request, 'Dadus servisu rai ona.')
			return _pasu_tuir_mai(request, emp, 'servisu')
	else:
		form = ServisuForm(instance=objects)
	context = {
		'form': form, 'group': group, 'hashid': hashid, 'emp': emp, 'cancel_url': f'/membro/{hashid}/',
		'back_url': 'membro-detail', 'back_args': [hashid], 'back_label': 'Detalha Membru',
		'title': 'Servisu Membru', 'legend': f'Servisu · {emp.nome}', **_fluxu_context(request, emp, 'servisu', 'Pasu 2 husi 3: servisu agora.')
	}
	return render(request, 'membro/servisu_form.html', context)

