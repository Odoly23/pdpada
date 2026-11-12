from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.urls import reverse
from django.shortcuts import get_object_or_404, render
from config import roles
from config.decorators import allowed_users
from config.user_utils import c_user_group
from membro.models import Historia

LIMITE = 3000

# ikon dan warna tombol filter per jenis aksi (urutan tampil = urutan di sini; aksi lain menyusul)
AKSAUN_STYLE = {
	'Kria': ('fa-plus-circle', 'info'), 'Edita': ('fa-pencil', 'warn'), 'Aprova': ('fa-check-circle', 'ok'),
	'Rejeita': ('fa-times-circle', 'bad'), 'Aloka': ('fa-sitemap', 'info'), 'Edita Pozisaun': ('fa-pencil', 'warn'),
	'Hamoos': ('fa-trash', 'bad'), 'Hamoos Pozisaun': ('fa-trash', 'bad'), 'Ekspor': ('fa-download', 'dark'),
	'Hare Dokumentu': ('fa-file-pdf-o', 'dark'),
}


def historia_filters(current):
	"""Tombol filter jenis aksi: 'Hotu' + satu tombol per jenis aksi yang ada, dengan hitungan dan status aktif."""
	counts = dict(Historia.objects.order_by().values_list('aksaun').annotate(n=Count('id')))
	base = reverse('historia-list')
	order = list(AKSAUN_STYLE)
	names = sorted(counts, key=lambda n: (order.index(n) if n in order else len(order), n))
	filters = [{'label': 'Hotu', 'url': base, 'icon': 'fa-th-list', 'kind': 'all', 'count': sum(counts.values()), 'active': current not in counts}]
	for name in names:
		icon, kind = AKSAUN_STYLE.get(name, ('fa-circle-o', 'info'))
		filters.append({'label': name, 'url': f'{base}?aksaun={name.replace(" ", "+")}', 'icon': icon, 'kind': kind,
			'count': counts[name], 'active': current == name})
	return filters


@login_required
@allowed_users(allowed_roles=roles.HISTORIA_ROLES)
def HistoriaList(request):
	group = c_user_group(request.user)
	objects = Historia.objects.select_related('user', 'membro')
	aksaun = request.GET.get('aksaun', '')
	if aksaun:
		objects = objects.filter(aksaun=aksaun)
	context = {
		'group': group, 'objects': objects[:LIMITE], 'limite': LIMITE,
		'filters': historia_filters(aksaun),
		'title': 'Historia Mudansa Data', 'legend': 'Historia Mudansa Data'
	}
	return render(request, 'membro/historia_list.html', context)


@login_required
@allowed_users(allowed_roles=roles.HISTORIA_ROLES)
def HistoriaDetail(request, pk):
	"""Detalhe lengkap satu rekaman historia (daftar hanya menampilkan ringkasan)."""
	group = c_user_group(request.user)
	obj = get_object_or_404(Historia.objects.select_related('user', 'membro'), pk=pk)
	context = {
		'group': group, 'obj': obj, 'can_membro': bool(obj.membro_id) and group in roles.LISTA_ROLES,
		'title': 'Detalhe Historia', 'legend': 'Detalhe Historia'
	}
	return render(request, 'membro/historia_detail.html', context)
