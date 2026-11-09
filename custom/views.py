from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, ProtectedError
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from config import roles
from config.decorators import allowed_users
from config.user_utils import c_user_group
from custom.forms import VillageForm, AldeiaForm, OrganizasaunForm, YearForm
from custom.models import AdministrativePost, Village, Aldeia, Organizasaun, Year


# ---------- dropdown AJAX (Suku -> Aldeia) ----------
@login_required
def load_posts(request):
	mun_id = request.GET.get('municipality')
	posts = AdministrativePost.objects.filter(municipality_id=mun_id).order_by('name') if (mun_id or '').isdigit() else []
	return render(request, 'custom/post_dropdown.html', {'posts': posts})


@login_required
def load_villages(request):
	post_id = request.GET.get('post')
	villages = Village.objects.filter(administrativepost_id=post_id).order_by('name') if (post_id or '').isdigit() else []
	return render(request, 'custom/village_dropdown.html', {'villages': villages})


@login_required
def load_aldeias(request):
	village_id = request.GET.get('village')
	aldeias = Aldeia.objects.filter(village_id=village_id).order_by('name') if (village_id or '').isdigit() else []
	return render(request, 'custom/aldeia_dropdown.html', {'aldeias': aldeias})


# ---------- data master (Admin) ----------
MASTER = {
	'suku': {'model': Village, 'form': VillageForm, 'label': 'Suku'},
	'aldeia': {'model': Aldeia, 'form': AldeiaForm, 'label': 'Aldeia'},
	'organizasaun': {'model': Organizasaun, 'form': OrganizasaunForm, 'label': 'Organizasaun'},
	'ano': {'model': Year, 'form': YearForm, 'label': 'Tinan'},
}


def _master(tipu):
	if tipu not in MASTER:
		raise Http404
	return MASTER[tipu]


def _rows(tipu):
	if tipu == 'suku':
		qs = Village.objects.annotate(a=Count('aldeia', distinct=True), m=Count('membro', distinct=True))
		return ['Naran Suku', 'Total Aldeia', 'Total Membru'], [(o, [o.name, o.a, o.m]) for o in qs]
	if tipu == 'aldeia':
		qs = Aldeia.objects.select_related('village').annotate(m=Count('membro'))
		return ['Suku', 'Naran Aldeia', 'Total Membru'], [(o, [o.village, o.name, o.m]) for o in qs]
	if tipu == 'organizasaun':
		qs = Organizasaun.objects.annotate(m=Count('membro'))
		return ['Kódigu', 'Naran', 'Ativu', 'Total Membru'], [(o, [o.code, o.name, 'Sim' if o.is_active else 'Lae', o.m]) for o in qs]
	qs = Year.objects.annotate(m=Count('membro'))
	return ['Tinan', 'Ativu', 'Total Membru'], [(o, [o.year, 'Sim' if o.is_active else 'Lae', o.m]) for o in qs]


@login_required
@allowed_users(allowed_roles=[roles.ADMIN])
def MasterList(request, tipu):
	cfg = _master(tipu)
	headers, rows = _rows(tipu)
	context = {
		'group': c_user_group(request.user), 'tipu': tipu, 'headers': headers, 'rows': rows,
		'title': f'Lista {cfg["label"]}', 'legend': f'Lista {cfg["label"]}'
	}
	return render(request, 'custom/master_list.html', context)


def _master_form(request, tipu, instance=None):
	cfg = _master(tipu)
	if request.method == 'POST':
		form = cfg['form'](request.POST, instance=instance)
		if form.is_valid():
			obj = form.save(commit=False)
			if tipu == 'suku' and not obj.administrativepost_id:
				obj.administrativepost = AdministrativePost.objects.order_by('id').first()
			obj.save()
			messages.success(request, 'Rai ho Susesu!.')
			return redirect('master-list', tipu)
	else:
		form = cfg['form'](instance=instance)
	acao = 'Edita' if instance else 'Aumenta'
	context = {
		'form': form, 'group': c_user_group(request.user), 'cancel_url': f'/custom/master/{tipu}/',
		'back_url': 'master-list', 'back_args': [tipu], 'back_label': f'Lista {cfg["label"]}',
		'title': f'{acao} {cfg["label"]}', 'legend': f'{acao} {cfg["label"]}'
	}
	return render(request, 'main/form.html', context)


@login_required
@allowed_users(allowed_roles=[roles.ADMIN])
def MasterAdd(request, tipu):
	return _master_form(request, tipu)


@login_required
@allowed_users(allowed_roles=[roles.ADMIN])
def MasterUpdate(request, tipu, pk):
	obj = get_object_or_404(_master(tipu)['model'], pk=pk)
	return _master_form(request, tipu, obj)


@login_required
@allowed_users(allowed_roles=[roles.ADMIN])
@require_POST
def MasterDel(request, tipu, pk):
	obj = get_object_or_404(_master(tipu)['model'], pk=pk)
	try:
		obj.delete()
		messages.warning(request, 'Hamoos ho Susesu!.')
	except ProtectedError:
		messages.error(request, 'La bele hamoos: iha data seluk ne\'ebé uza ona.')
	return redirect('master-list', tipu)


@login_required
@allowed_users(allowed_roles=[roles.ADMIN])
@require_POST
def AnoAktiva(request, pk):
	obj = get_object_or_404(Year, pk=pk)
	obj.is_active = True
	obj.save()
	messages.success(request, f'Tinan {obj.year} ativu ona.')
	return redirect('master-list', 'ano')
