from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db.models.functions import Lower
from django.shortcuts import render
from config import roles
from config.decorators import allowed_users
from config.user_utils import c_user_group, membro_scope

LIMITE_GRUPU = 100


def _group_members(members, key):
	"""Kumpulkan membru per kunci (dalam urutan kunci pertama muncul)."""
	groups = {}
	for m in members:
		groups.setdefault(key(m), []).append(m)
	return [g for g in groups.values() if len(g) > 1]


@login_required
@allowed_users(allowed_roles=roles.DUPLIKAT_ROLES)
def MembroDupla(request):
	"""Membru dobel potensial: naran + data moris hanesan, ka Nu. Telemovel hanesan.
	Nu. Eleitoral dobel sudah ditolak sistema; ini menangkap kasus yang lolos (salah ketik Nu. Eleitoral)."""
	group = c_user_group(request.user)
	qs = membro_scope(request.user).select_related('village', 'aldeia', 'organizasaun')

	nama_keys = (qs.annotate(nome_key=Lower('nome')).values('nome_key', 'date_of_birth')
		.annotate(total=Count('id')).filter(total__gt=1).order_by('nome_key')[:LIMITE_GRUPU])
	nama_keys = list(nama_keys)
	groups_nome = []
	if nama_keys:
		members = (qs.annotate(nome_key=Lower('nome')).filter(
			nome_key__in={k['nome_key'] for k in nama_keys}, date_of_birth__in={k['date_of_birth'] for k in nama_keys}).order_by('nome'))
		groups_nome = _group_members(members, lambda m: (m.nome.lower(), m.date_of_birth))

	phone_keys = list(qs.exclude(telefone__isnull=True).exclude(telefone='').values('telefone')
		.annotate(total=Count('id')).filter(total__gt=1).order_by('telefone')[:LIMITE_GRUPU])
	groups_tel = []
	if phone_keys:
		members = qs.filter(telefone__in=[k['telefone'] for k in phone_keys]).order_by('telefone', 'nome')
		groups_tel = _group_members(members, lambda m: m.telefone)

	context = {
		'group': group, 'groups_nome': groups_nome, 'groups_tel': groups_tel,
		'title': 'Membru Dupla Potensial', 'legend': 'Membru Dupla Potensial'
	}
	return render(request, 'membro/dupla.html', context)
