from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from config import roles
from config.decorators import allowed_users
from config.user_utils import c_user_group, c_user_scope, alokasaun_scope
from custom.models import Village, Aldeia, Organizasaun, Year
from membro.forms import AlokasaunForm
from membro.models import Alokasaun
from membro.utils import log_historia, apply_alokasaun_filters


@login_required
@allowed_users(allowed_roles=roles.STRUKTURA_ROLES)
def AlokasaunList(request):
	group = c_user_group(request.user)
	objects = alokasaun_scope(request.user).select_related('membro', 'village', 'aldeia', 'organizasaun')
	objects = list(apply_alokasaun_filters(objects, request.GET))
	# berapa orang yang pernah/sedang memegang posisi yang sama (data lama tetap tersimpan setelah termina)
	keys = ('nivel', 'pozisaun', 'village_id', 'aldeia_id', 'organizasaun_id')
	pernah = {tuple(r[k] for k in keys): r['n'] for r in Alokasaun.objects.order_by().values(*keys).annotate(n=Count('id'))}
	for obj in objects:
		obj.pernah = pernah.get((obj.nivel, obj.pozisaun, obj.village_id, obj.aldeia_id, obj.organizasaun_id), 1)
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
def AlokasaunTermina(request, pk):
	"""Akhiri pozisaun: data lama tetap tersimpan (ativu Lae + data termina) dan membru bisa dialokasikan lagi."""
	obj = get_object_or_404(Alokasaun, pk=pk)
	if obj.ativu != 'Sim':
		messages.info(request, 'Pozisaun ne\'e termina ona.')
		return redirect('alokasaun-list')
	obj.ativu = 'Lae'
	obj.data_termina = obj.data_termina or max(timezone.localdate(), obj.data_hahu)
	obj.datetime = timezone.now()
	obj.user = request.user
	obj.save()
	log_historia(request.user, obj.membro, 'Termina Pozisaun', f'{obj.pozisaun} {obj.nivel} {obj.unit() or ""}'.strip())
	messages.success(request, f'Pozisaun termina ona. {obj.membro.nome} bele hetan pozisaun foun.')
	return redirect('alokasaun-list')


@login_required
@allowed_users(allowed_roles=roles.ALOKA_ROLES)
@require_POST
def AlokasaunDel(request, pk):
	obj = get_object_or_404(Alokasaun, pk=pk)
	log_historia(request.user, obj.membro, 'Hamoos Pozisaun', f'{obj.pozisaun} {obj.nivel} {obj.unit() or ""}'.strip())
	obj.delete()
	messages.warning(request, 'Hamoos ho Susesu!.')
	return redirect('alokasaun-list')


def _unit_scope(user):
	"""Suku, aldeia dan organisasi yang masuk dalam wilayah user."""
	group, scope = c_user_group(user), c_user_scope(user)
	villages, aldeias, orgs = Village.objects.none(), Aldeia.objects.none(), Organizasaun.objects.none()
	if group in roles.POSTU_ROLES:
		villages, aldeias, orgs = Village.objects.all(), Aldeia.objects.all(), Organizasaun.objects.filter(is_active=True)
	elif scope and group in roles.SUKU_ROLES and scope.village_id:
		villages, aldeias = Village.objects.filter(pk=scope.village_id), Aldeia.objects.filter(village_id=scope.village_id)
	elif scope and group in roles.ALDEIA_ROLES and scope.aldeia_id:
		aldeias = Aldeia.objects.filter(pk=scope.aldeia_id)
		villages = Village.objects.filter(pk=scope.aldeia.village_id)
	elif scope and group in roles.ORG_ROLES and scope.organizasaun_id:
		orgs = Organizasaun.objects.filter(pk=scope.organizasaun_id)
	return villages, aldeias.select_related('village'), orgs


@login_required
@allowed_users(allowed_roles=roles.STRUKTURA_ROLES)
def AlokasaunDash(request):
	"""Dashboard Struktura PD: siapa memegang posisi apa, dan kelengkapannya per suku/aldeia/organisasi."""
	group = c_user_group(request.user)
	villages, aldeias, orgs = _unit_scope(request.user)
	aktivu = list(Alokasaun.objects.filter(ativu='Sim').select_related('membro'))
	postu = {a.pozisaun: a for a in aktivu if a.nivel == 'Postu'}
	suku = {(a.village_id, a.pozisaun): a for a in aktivu if a.nivel == 'Suku'}
	org = {(a.organizasaun_id, a.pozisaun): a for a in aktivu if a.nivel == 'Organizasaun'}
	aldeia_hold = {(a.aldeia_id, a.pozisaun): a for a in aktivu if a.nivel == 'Aldeia'}
	aldeias = list(aldeias)
	rows_suku = []
	for v in villages:
		mine = [a for a in aldeias if a.village_id == v.pk]
		rows_suku.append({
			'v': v, 'coord': suku.get((v.pk, 'Coordenador')), 'sekr': suku.get((v.pk, 'Sekretariu')),
			'a_total': len(mine),
			'a_coord': sum(1 for a in mine if (a.pk, 'Coordenador') in aldeia_hold),
			'a_sekr': sum(1 for a in mine if (a.pk, 'Sekretariu') in aldeia_hold),
		})
	rows_aldeia = [{'a': a, 'coord': aldeia_hold.get((a.pk, 'Coordenador')), 'sekr': aldeia_hold.get((a.pk, 'Sekretariu'))} for a in aldeias]
	rows_org = [{'o': o, 'coord': org.get((o.pk, 'Coordenador')), 'sekr': org.get((o.pk, 'Sekretariu'))} for o in orgs]
	context = {
		'group': group, 'show_postu': group in roles.POSTU_ROLES,
		'can_aloka': group in roles.ALOKA_ROLES, 'can_link': group in roles.POSTU_ROLES,
		'postu': [(p, postu.get(p)) for p in ('Presidente', 'Coordenador', 'Sekretariu')],
		'rows_suku': rows_suku, 'rows_aldeia': rows_aldeia, 'rows_org': rows_org,
		'ano_ativu_obj': Year.objects.filter(is_active=True).first(),
		'title': 'Struktura PD', 'legend': 'Struktura PD'
	}
	return render(request, 'membro/alokasaun_dash.html', context)
