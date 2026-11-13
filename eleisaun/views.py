from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from config import roles
from config.decorators import allowed_users
from config.user_utils import c_user_group
from eleisaun.forms import EleisaunForm, FiskaisForm, ResultadoForm, TempatForm
from eleisaun.models import Eleisaun, FiskaisTempat, Resultado, TempatVoting
from eleisaun.utils import eleisaun_ativu, komparasaun_data, live_payload
from membro.utils import log_historia

NOME_LOG = 'Eleisaun'


@login_required
@allowed_users(allowed_roles=roles.VIEW_ROLES)
def LiveDashboard(request):
	"""Dashboard live layar penuh (halaman mandiri: tanpa menu, jam dinding, layar tetap menyala)."""
	return render(request, 'eleisaun/live.html', {'data_url': reverse('eleisaun-live-data')})


@login_required
@allowed_users(allowed_roles=roles.VIEW_ROLES)
def LiveData(request):
	response = JsonResponse(live_payload())
	response['Cache-Control'] = 'no-store'
	return response


@login_required
@allowed_users(allowed_roles=roles.POSTU_ROLES)
def Komparasaun(request):
	el, rows, totals = komparasaun_data()
	context = {
		'group': c_user_group(request.user), 'el': el, 'rows': rows, 'totals': totals,
		'chart': {'label': [r['suku'] for r in rows], 'membru': [r['membru'] for r in rows], 'votos': [r['votos'] for r in rows]},
		'title': 'Komparasaun Membru no Votu', 'legend': 'Komparasaun Membru no Votu',
		'meta_description': 'Perbandingan total membru dan total votu Partido Democratico per suku, Postu Dom Aleixo.',
	}
	return render(request, 'eleisaun/komparasaun.html', context)


@login_required
@allowed_users(allowed_roles=roles.FISKAIS_ROLES)
def ResultadoInput(request):
	"""Fiskais input hasil votu PD di tempatnya: sekali submit, lalu terkunci sampai Admin membuka lagi."""
	fk = FiskaisTempat.objects.select_related('tempat__village').filter(user=request.user).first()
	el = eleisaun_ativu()
	context = {'group': c_user_group(request.user), 'fk': fk, 'el': el, 'locked': False, 'res': None, 'form': None,
		'title': 'Input Rezultadu', 'legend': 'Input Rezultadu'}
	if not fk or not el or not fk.tempat.ativu:
		return render(request, 'eleisaun/input.html', context)
	res = Resultado.objects.filter(eleisaun=el, tempat=fk.tempat).first()
	context['res'] = res
	if res and res.submetidu:
		context['locked'] = True
		return render(request, 'eleisaun/input.html', context)
	if request.method == 'POST':
		form = ResultadoForm(request.POST, request.FILES, instance=res)
		if form.is_valid():
			obj = form.save(commit=False)
			obj.eleisaun, obj.tempat = el, fk.tempat
			obj.submetidu, obj.submetidu_em, obj.submetidu_husi = True, timezone.now(), request.user
			try:
				with transaction.atomic():
					obj.save()
			except IntegrityError:  # submit ganda bersamaan: satu saja yang diterima
				messages.error(request, "Rezultadu ba tempat ne'e submete ona.")
				return redirect('eleisaun-input')
			log_historia(request.user, None, 'Resultado Submete', f'{fk.tempat.naran} · votu PD: {obj.votos_partidu}', nome=NOME_LOG)
			messages.success(request, "Rezultadu submete ona. Dadus taka; Admin bele loke fali se presiza koriji.")
			return redirect('eleisaun-input')
	else:
		form = ResultadoForm(instance=res)
	context['form'] = form
	return render(request, 'eleisaun/input.html', context)


@login_required
@allowed_users(allowed_roles=roles.FISKAIS_ROLES + roles.POSTU_ROLES)
def ResultadoFile(request, pk, kind):
	"""Foto hasil dari penyimpanan privat: Postu, atau fiskais yang men-submit sendiri."""
	res = get_object_or_404(Resultado.objects.select_related('tempat'), pk=pk)
	if c_user_group(request.user) == roles.FISKAIS and res.submetidu_husi_id != request.user.pk:
		raise Http404
	if kind != 'foto':
		raise Http404
	field, ctype, name = res.foto, 'image/jpeg', 'foto-rezultadu.jpg'
	if not field:
		raise Http404
	try:
		handle = field.storage.open(field.name, 'rb')
	except (FileNotFoundError, OSError):
		raise Http404
	log_historia(request.user, None, 'Hare Resultado', f'{kind} · {res.tempat.naran}', nome=NOME_LOG)
	response = FileResponse(handle, content_type=ctype)
	response['Content-Disposition'] = f'inline; filename="{name}"'
	response['X-Content-Type-Options'] = 'nosniff'
	response['Cache-Control'] = 'private, no-store'
	return response


@login_required
@allowed_users(allowed_roles=roles.ELEISAUN_ADMIN_ROLES)
def EleisaunAdmin(request):
	el = eleisaun_ativu()
	resultados = Resultado.objects.select_related('tempat', 'submetidu_husi').filter(eleisaun=el) if el else Resultado.objects.none()
	context = {
		'group': c_user_group(request.user), 'el': el, 'eleisaun_list': Eleisaun.objects.all(),
		'tempat_list': TempatVoting.objects.select_related('village', 'aldeia').prefetch_related('fiskais__user'),
		'fiskais_list': FiskaisTempat.objects.select_related('user', 'tempat'), 'resultados': resultados,
		'title': 'Eleisaun no Tempat', 'legend': 'Eleisaun no Tempat',
	}
	return render(request, 'eleisaun/admin.html', context)


def _admin_form(request, form_cls, legend, aksaun, detalhe, sucesso):
	form = form_cls(request.POST or None)
	if request.method == 'POST' and form.is_valid():
		obj = form.save()
		log_historia(request.user, None, aksaun, detalhe(obj), nome=NOME_LOG)
		messages.success(request, sucesso)
		return redirect('eleisaun-admin')
	return render(request, 'main/form.html', {
		'form': form, 'group': c_user_group(request.user), 'cancel_url': reverse('eleisaun-admin'),
		'back_url': 'eleisaun-admin', 'back_label': 'Eleisaun no Tempat', 'title': legend, 'legend': legend})


@login_required
@allowed_users(allowed_roles=roles.ELEISAUN_ADMIN_ROLES)
def EleisaunAdd(request):
	return _admin_form(request, EleisaunForm, 'Aumenta Eleisaun', 'Eleisaun Foun', lambda o: f'{o.naran} ({o.tinan})', 'Eleisaun aumenta ona.')


@login_required
@allowed_users(allowed_roles=roles.ELEISAUN_ADMIN_ROLES)
def TempatAdd(request):
	return _admin_form(request, TempatForm, 'Aumenta Tempat Votasaun', 'Tempat Foun', lambda o: f'{o.naran} · {o.village}', 'Tempat aumenta ona.')


@login_required
@allowed_users(allowed_roles=roles.ELEISAUN_ADMIN_ROLES)
def FiskaisAdd(request):
	return _admin_form(request, FiskaisForm, 'Aloka Fiskais ba Tempat', 'Fiskais Foun', lambda o: f'{o.user.get_username()} @ {o.tempat.naran}', 'Fiskais aloka ona.')


@login_required
@allowed_users(allowed_roles=roles.ELEISAUN_ADMIN_ROLES)
@require_POST
def FiskaisDel(request, pk):
	obj = get_object_or_404(FiskaisTempat.objects.select_related('user', 'tempat'), pk=pk)
	log_historia(request.user, None, 'Hamoos Fiskais', f'{obj.user.get_username()} husi {obj.tempat.naran}', nome=NOME_LOG)
	obj.delete()
	messages.warning(request, 'Hamoos ho Susesu!.')
	return redirect('eleisaun-admin')


@login_required
@allowed_users(allowed_roles=roles.ELEISAUN_ADMIN_ROLES)
@require_POST
def EleisaunToggle(request, pk):
	obj = get_object_or_404(Eleisaun, pk=pk)
	obj.ativu = not obj.ativu
	obj.save()
	log_historia(request.user, None, 'Eleisaun Live', f'{obj.naran}: ' + ('live aktiva' if obj.ativu else 'live taka'), nome=NOME_LOG)
	messages.success(request, 'Dashboard live aktiva.' if obj.ativu else 'Dashboard live taka.')
	return redirect('eleisaun-admin')


@login_required
@allowed_users(allowed_roles=roles.ELEISAUN_ADMIN_ROLES)
@require_POST
def ResultadoLoke(request, pk):
	"""Admin membuka kunci hasil supaya fiskais bisa memperbaiki dan submit lagi (data lama tetap ada)."""
	obj = get_object_or_404(Resultado.objects.select_related('tempat'), pk=pk)
	if obj.submetidu:
		obj.submetidu = False
		obj.save()
		log_historia(request.user, None, 'Loke Resultado', f'{obj.tempat.naran} loke fali ba fiskais', nome=NOME_LOG)
		messages.success(request, f'Rezultadu {obj.tempat.naran} loke fali.')
	return redirect('eleisaun-admin')
