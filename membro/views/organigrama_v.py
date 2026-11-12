from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from config import roles
from config.decorators import allowed_users
from config.user_utils import c_user_group
from membro.forms import OrgPozisaunForm, OrgResponsavelForm
from membro.models import OrgPozisaun, OrgResponsavel
from membro.utils import log_historia


def _tree():
	"""Pohon posisi: [{'pos', 'resp', 'children'}] + daftar datar urut untuk tabel."""
	posisi = list(OrgPozisaun.objects.filter(ativu=True).prefetch_related('responsavel__membro'))
	nodes = {p.pk: {'pos': p, 'resp': list(p.responsavel.all()), 'tarefas': p.tarefas(), 'children': []} for p in posisi}
	roots = []
	for p in posisi:
		parent = nodes.get(p.parent_id)
		(parent['children'] if parent else roots).append(nodes[p.pk])
	return roots, [nodes[p.pk] for p in posisi]


@login_required
@allowed_users(allowed_roles=roles.STRUKTURA_ROLES)
def Organigrama(request):
	"""Organigrama komisaun: bagan posisi + responsavel, dan tabel Pozisaun | Responsavel | Deskrisaun Tarefas | Obs."""
	group = c_user_group(request.user)
	roots, flat = _tree()
	context = {
		'group': group, 'roots': roots, 'flat': flat, 'can_manage': group in roles.ALOKA_ROLES,
		'n_pozisaun': len(flat), 'n_responsavel': sum(len(n['resp']) for n in flat),
		'n_kosong': sum(1 for n in flat if not n['resp']),
		'title': 'Organigrama', 'legend': 'Organigrama',
		'meta_description': 'Organigrama komisaun Partido Democratico, Postu Dom Aleixo: pozisaun, responsavel no tarefas.',
	}
	return render(request, 'membro/organigrama.html', context)


def _form_page(request, form, legend, back='organigrama'):
	return render(request, 'main/form.html', {
		'form': form, 'group': c_user_group(request.user), 'cancel_url': '/membro/organigrama/',
		'back_url': back, 'back_label': 'Organigrama', 'title': legend, 'legend': legend})


@login_required
@allowed_users(allowed_roles=roles.ALOKA_ROLES)
def OrgPozisaunAdd(request):
	form = OrgPozisaunForm(request.POST or None)
	if request.method == 'POST' and form.is_valid():
		obj = form.save()
		log_historia(request.user, None, 'Organigrama', f'Pozisaun foun: {obj.naran}', nome='Organigrama')
		messages.success(request, 'Pozisaun aumenta ona.')
		return redirect('organigrama')
	return _form_page(request, form, 'Aumenta Pozisaun')


@login_required
@allowed_users(allowed_roles=roles.ALOKA_ROLES)
def OrgPozisaunUpdate(request, pk):
	obj = get_object_or_404(OrgPozisaun, pk=pk)
	form = OrgPozisaunForm(request.POST or None, instance=obj)
	if request.method == 'POST' and form.is_valid():
		form.save()
		log_historia(request.user, None, 'Organigrama', f'Pozisaun atualiza: {obj.naran}', nome='Organigrama')
		messages.success(request, 'Pozisaun atualiza ona.')
		return redirect('organigrama')
	return _form_page(request, form, 'Edita Pozisaun')


@login_required
@allowed_users(allowed_roles=roles.ALOKA_ROLES)
@require_POST
def OrgPozisaunDel(request, pk):
	obj = get_object_or_404(OrgPozisaun, pk=pk)
	if obj.sub.exists():
		messages.error(request, 'Pozisaun ne\'e iha pozisaun okos. Muda ka hamoos pozisaun okos uluk.')
		return redirect('organigrama')
	log_historia(request.user, None, 'Organigrama', f'Pozisaun hamoos: {obj.naran}', nome='Organigrama')
	obj.delete()
	messages.warning(request, 'Hamoos ho Susesu!.')
	return redirect('organigrama')


@login_required
@allowed_users(allowed_roles=roles.ALOKA_ROLES)
def OrgResponsavelAdd(request, pk):
	pos = get_object_or_404(OrgPozisaun, pk=pk)
	inicial = {'urutan': (pos.responsavel.count() + 1)}
	form = OrgResponsavelForm(request.POST or None, initial=inicial)
	if request.method == 'POST' and form.is_valid():
		obj = form.save(commit=False)
		obj.pozisaun = pos
		obj.save()
		log_historia(request.user, obj.membro, 'Organigrama', f'Responsavel {obj.naran} iha {pos.naran}', nome=obj.naran)
		messages.success(request, 'Responsavel aumenta ona.')
		return redirect('organigrama')
	return _form_page(request, form, f'Aumenta Responsavel · {pos.naran}')


@login_required
@allowed_users(allowed_roles=roles.ALOKA_ROLES)
def OrgResponsavelUpdate(request, pk):
	obj = get_object_or_404(OrgResponsavel.objects.select_related('pozisaun'), pk=pk)
	form = OrgResponsavelForm(request.POST or None, instance=obj)
	if request.method == 'POST' and form.is_valid():
		form.save()
		log_historia(request.user, obj.membro, 'Organigrama', f'Responsavel atualiza: {obj.naran} iha {obj.pozisaun.naran}', nome=obj.naran)
		messages.success(request, 'Responsavel atualiza ona.')
		return redirect('organigrama')
	return _form_page(request, form, f'Edita Responsavel · {obj.pozisaun.naran}')


@login_required
@allowed_users(allowed_roles=roles.ALOKA_ROLES)
@require_POST
def OrgResponsavelDel(request, pk):
	obj = get_object_or_404(OrgResponsavel.objects.select_related('pozisaun'), pk=pk)
	log_historia(request.user, obj.membro, 'Organigrama', f'Responsavel hasai: {obj.naran} husi {obj.pozisaun.naran}', nome=obj.naran)
	obj.delete()
	messages.warning(request, 'Hamoos ho Susesu!.')
	return redirect('organigrama')
