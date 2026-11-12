import datetime
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from config import roles
from config.decorators import allowed_users
from config.user_utils import c_user_group, membro_scope
from custom.models import Year, Village, Aldeia, Organizasaun
from membro.models import Membro, Alokasaun
from users.utils import c_user_emp

ROLE_NAME = dict(roles.ROLE_LABELS)
SEX_COUNTS = {'mane': Count('id', filter=Q(sex='Mane')), 'feto': Count('id', filter=Q(sex='Feto'))}
BAR_ROWS = 12  # lebih dari ini grafik dibuat mendatar agar 50+ aldeia tetap terbaca


def _level(group):
	"""Tingkat tampilan peran: postu (semua suku/aldeia), suku, aldeia atau org."""
	if group in roles.POSTU_ROLES:
		return 'postu'
	if group in roles.SUKU_ROLES:
		return 'suku'
	if group in roles.ALDEIA_ROLES:
		return 'aldeia'
	return 'org'


def _banner(group, e):
	"""Dua baris judul: peran dan wilayahnya."""
	name = ROLE_NAME.get(group, '').upper()
	if group in roles.POSTU_ROLES:
		return name, 'POSTU DOM ALEIXO'
	if e and group in roles.SUKU_ROLES and e.village_id:
		return name, f'SUKU {e.village.name.upper()}'
	if e and group in roles.ALDEIA_ROLES and e.aldeia_id:
		return name, f'ALDEIA {e.aldeia.name.upper()} · SUKU {e.aldeia.village.name.upper()}'
	if e and group in roles.ORG_ROLES and e.organizasaun_id:
		return name, f'ORGANIZASAUN {e.organizasaun.code}'
	return name, 'SGDM-PDPADA'


def _list_url(group, **params):
	"""Tautan ke lista membru terfilter; kosong untuk peran yang hanya boleh melihat rekapitulasi."""
	if group not in roles.LISTA_ROLES:
		return ''
	query = '&'.join(f'{k}={v}' for k, v in params.items())
	return reverse('membro-list') + ('?' + query if query else '')


def _counts(qs, field):
	"""{id: {n, mane, feto}} jumlah membru per `field` (satu query)."""
	return {r[field]: r for r in qs.order_by().values(field).annotate(n=Count('id'), **SEX_COUNTS)}


def _units(level, e, aldeia_rows, suku_rows):
	"""Suku dan aldeia yang tampil sesuai wilayah peran. Postu: semua; suku: sukunya; aldeia: aldeianya;
	organisasi: hanya yang punya anggota organisasinya."""
	villages, aldeias = Village.objects.all(), Aldeia.objects.select_related('village')
	if level == 'suku':
		villages, aldeias = villages.filter(pk=e.village_id) if e else villages.none(), aldeias.filter(village_id=e.village_id) if e else aldeias.none()
	elif level == 'aldeia':
		villages = villages.filter(pk=e.aldeia.village_id) if e and e.aldeia_id else villages.none()
		aldeias = aldeias.filter(pk=e.aldeia_id) if e else aldeias.none()
	elif level == 'org':
		villages, aldeias = villages.filter(pk__in=list(suku_rows)), aldeias.filter(pk__in=list(aldeia_rows))
	return villages, aldeias


def _chart(labels, values, title, mane=None, feto=None, horizontal=None):
	"""Data grafik; `mane`/`feto` (jika ada) membuat grafik berkelompok perbandingan Mane dan Feto per label."""
	horizontal = len(labels) > BAR_ROWS if horizontal is None else horizontal
	per = 2 if mane is not None else 1  # grafik mendatar dengan dua batang per label perlu ruang lebih
	return {'label': labels, 'obj': values, 'mane': mane, 'feto': feto, 'title': title, 'horizontal': horizontal,
		'height': 90 + 26 * per * len(labels) if horizontal else 360}


@login_required
@allowed_users(allowed_roles=roles.VIEW_ROLES)
def VarandaRekap(request):
	"""Varanda: total, total per suku, kartu per aldeia dan grafik, hanya untuk wilayah peran (rekapitulasi)."""
	group = c_user_group(request.user)
	e = c_user_emp(request.user)
	level = _level(group)
	ano = Year.objects.filter(is_active=True).first()
	qs = membro_scope(request.user).filter(year=ano) if ano else membro_scope(request.user)
	agg = qs.aggregate(total=Count('id'), mane=Count('id', filter=Q(sex='Mane')), feto=Count('id', filter=Q(sex='Feto')),
		baru=Count('id', filter=Q(datetime__gte=timezone.now() - datetime.timedelta(days=30))))
	total = agg['total']
	suku_rows, aldeia_rows = _counts(qs, 'village_id'), _counts(qs, 'aldeia_id')
	villages, aldeias = _units(level, e, aldeia_rows, suku_rows)

	objects1 = []
	for x in villages:
		objects1.append([x, suku_rows.get(x.pk, {}).get('n', 0)])
	objects2 = []
	for x in aldeias:
		row = aldeia_rows.get(x.pk, {})
		objects2.append({'obj': x, 'n': row.get('n', 0), 'mane': row.get('mane', 0), 'feto': row.get('feto', 0),
			'url': _list_url(group, aldeia=x.pk)})

	suku_cards, info = [], None
	if level == 'postu':  # Postu: hitung per suku dulu; aldeia baru muncul setelah suku diklik
		for x, n in objects1:
			row = suku_rows.get(x.pk, {})
			suku_cards.append({'obj': x, 'n': n, 'mane': row.get('mane', 0), 'feto': row.get('feto', 0), 'url': reverse('membro-suku', args=[x.pk])})
		objects2 = []
		# Struktura suku lengkap = Coordenador dan Sekretariu suku sama-sama sudah dialokasikan
		lengkap = Alokasaun.objects.filter(ativu='Sim', nivel='Suku', village__isnull=False).values('village_id').annotate(
			k=Count('pozisaun', distinct=True)).filter(k__gte=2).count()
		info = {'mane': agg['mane'], 'feto': agg['feto'], 'baru': agg['baru'], 'lengkap': lengkap, 'suku': len(suku_cards)}

	if level == 'postu':
		chart = _chart([c['obj'].name for c in suku_cards], [c['n'] for c in suku_cards], 'Grafiku Mane no Feto Tuir Suku',
			[c['mane'] for c in suku_cards], [c['feto'] for c in suku_cards])
	elif level == 'aldeia':  # satu aldeia saja: grafik per organizasaun
		org = _counts(qs, 'organizasaun_id')
		names = {o.pk: o.code for o in Organizasaun.objects.filter(pk__in=[k for k in org if k])}
		keys = sorted(org, key=lambda k: names.get(k, 'zzz'))
		chart = _chart([names.get(k, 'Laiha organizasaun') for k in keys], [org[k]['n'] for k in keys], 'Grafiku Mane no Feto Tuir Organizasaun',
			[org[k]['mane'] for k in keys], [org[k]['feto'] for k in keys])
	else:
		chart = _chart([r['obj'].name for r in objects2], [r['n'] for r in objects2], 'Grafiku Mane no Feto Tuir Aldeia',
			[r['mane'] for r in objects2], [r['feto'] for r in objects2])

	context = {
		'group': group, 'role_label': ROLE_NAME.get(group, ''), 'e': e, 'level': level, 'banner': _banner(group, e),
		'total': total, 'total_url': _list_url(group), 'objects1': objects1, 'objects2': objects2, 'suku_cards': suku_cards, 'info': info, 'chart': chart,
		'can_list': group in roles.LISTA_ROLES, 'can_add': group in roles.INPUT_ROLES,
		'can_struktura': group in roles.STRUKTURA_ROLES, 'group_cards': False,
		'title': 'Varanda', 'legend': 'Varanda',
		'meta_description': 'SGDM-PDPADA: Sistema Jestaun Dadus Membru Partido Democratico, Postu Administrativu Dom Aleixo, Dili.',
	}
	return render(request, 'home/varanda_rekap.html', context)


@login_required
@allowed_users(allowed_roles=roles.VIEW_ROLES)
def PainelRekap(request):
	"""Painel: daftar TINAN | unit (suku, aldeia atau organizasaun sesuai peran) | grafik dengan unit terpilih menyala."""
	group = c_user_group(request.user)
	e = c_user_emp(request.user)
	level = _level(group)
	years = list(Year.objects.order_by('-year'))
	ano_id = request.GET.get('ano', '')
	ano = next((y for y in years if str(y.pk) == ano_id), None) or next((y for y in years if y.is_active), None)
	qs = membro_scope(request.user)
	if ano:
		qs = qs.filter(year=ano)
	sel = request.GET.get('u', '')
	sel = int(sel) if sel.isdigit() else 0
	linkable = bool(ano and ano.is_active)

	year_count = dict(membro_scope(request.user).order_by().values_list('year_id').annotate(n=Count('id')))
	objects1 = [[x, year_count.get(x.pk, 0), ano is not None and x.pk == ano.pk] for x in years]

	# unit daftar tengah: postu/org -> suku (detail aldeia saat dipilih); suku -> aldeia; aldeia -> organizasaun
	if level in ('postu', 'org'):
		unit_title, field, key = 'SUKU', 'village_id', 'village'
	elif level == 'suku':
		unit_title, field, key = 'ALDEIA', 'aldeia_id', 'aldeia'
	else:
		unit_title, field, key = 'ORGANIZASAUN', 'organizasaun_id', 'organizasaun'
	rows = _counts(qs, field)
	if field == 'village_id':
		villages, _ = _units(level, e, {}, rows)
		base = [(x.pk, x.name) for x in villages]
	elif field == 'aldeia_id':
		_, aldeias = _units(level, e, rows, {})
		base = [(x.pk, x.name) for x in aldeias]
	else:
		names = {o.pk: o.code for o in Organizasaun.objects.filter(pk__in=[k for k in rows if k])}
		base = [(k or 0, names.get(k, 'Laiha organizasaun')) for k in sorted(rows, key=lambda k: names.get(k, 'zzz'))]
	objects2, selected = [], None
	for pk, name in base:
		row = rows.get(pk or None, {}) if field == 'organizasaun_id' else rows.get(pk, {})
		item = {'id': pk, 'name': name, 'n': row.get('n', 0), 'mane': row.get('mane', 0), 'feto': row.get('feto', 0), 'active': pk == sel and sel != 0}
		if item['active']:
			selected = item
		objects2.append(item)

	aldeias_detail = []
	if selected and level in ('postu', 'org'):
		counts = _counts(qs.filter(village_id=sel), 'aldeia_id')
		for x in Aldeia.objects.filter(village_id=sel):
			if level == 'org' and x.pk not in counts:
				continue
			aldeias_detail.append([x, counts.get(x.pk, {}).get('n', 0), _list_url(group, aldeia=x.pk) if linkable else ''])

	labels = [r['name'] for r in objects2]
	chart = _chart(labels, [r['n'] for r in objects2], '', [r['mane'] for r in objects2], [r['feto'] for r in objects2])
	chart['selected'] = next((i for i, r in enumerate(objects2) if r['active']), -1)
	context = {
		'group': group, 'level': level, 'banner': _banner(group, e), 'ano': ano, 'unit_title': unit_title,
		'objects1': objects1, 'objects2': objects2, 'selected': selected, 'aldeias': aldeias_detail, 'chart': chart,
		'total': sum(r['n'] for r in objects2),
		'selected_url': _list_url(group, **{key: sel}) if selected and linkable and key != 'organizasaun' else '',
		'can_add': group in roles.INPUT_ROLES,
		'title': 'Painel', 'legend': 'Painel',
		'meta_description': 'Painel SGDM-PDPADA: membru por tinan no suku, Partido Democratico, Postu Dom Aleixo.',
	}
	return render(request, 'membro/painel_rekap.html', context)


POZISAUN_LABEL = {'Presidente': 'Presidente', 'Coordenador': 'Cordenador', 'Sekretariu': 'Sekjer'}


@login_required
@allowed_users(allowed_roles=roles.POSTU_ROLES)
def SukuRekap(request, pk):
	"""Detalhe satu suku (peran Postu): pemimpin suku, total, dan tabel Suku | Aldeia | Naran Membru | Posisaun.
	Hanya naran, aldeia dan posisaun; Nu. Eleitoral, telepon dan dokumen tidak ditampilkan."""
	group = c_user_group(request.user)
	village = get_object_or_404(Village, pk=pk)
	ano = Year.objects.filter(is_active=True).first()
	qs = membro_scope(request.user).filter(village=village).select_related('aldeia')
	if ano:
		qs = qs.filter(year=ano)
	tot = qs.aggregate(
		total=Count('id'), mane=Count('id', filter=Q(sex='Mane')), feto=Count('id', filter=Q(sex='Feto')),
		ativu=Count('id', filter=Q(status='Ativu')), inativu=Count('id', filter=Q(status='Inativu')),
		falesidu=Count('id', filter=Q(status='Falesidu')))

	label, rank, leaders = {}, {}, {}
	holders = Alokasaun.objects.filter(ativu='Sim').filter(Q(village=village) | Q(aldeia__village=village) | Q(organizasaun__isnull=False, membro__village=village))
	for a in holders.select_related('aldeia', 'organizasaun').order_by('nivel', 'pozisaun'):
		pos = POZISAUN_LABEL.get(a.pozisaun, a.pozisaun)
		if a.nivel == 'Suku':
			label[a.membro_id], rank[a.membro_id] = f'{pos} Suku', (0 if a.pozisaun == 'Coordenador' else 0.5)
			leaders[a.pozisaun] = a.membro_id
		elif a.nivel == 'Aldeia':
			label.setdefault(a.membro_id, f'{pos} Aldeia {a.aldeia.name}')
			rank.setdefault(a.membro_id, 1)
		elif a.nivel == 'Organizasaun':
			label.setdefault(a.membro_id, f'{pos} {a.organizasaun.code}')
			rank.setdefault(a.membro_id, 2)
	members = sorted(qs, key=lambda m: (rank.get(m.pk, 3), m.aldeia.name, m.nome))
	rows = [{'aldeia': m.aldeia.name, 'nome': m.nome, 'pozisaun': label.get(m.pk, 'Membru')} for m in members]
	by_id = {m.pk: m for m in members}
	pemimpin = []
	for key, name in (('Coordenador', 'Cordenador Suku'), ('Sekretariu', 'Sekjer Suku')):
		m = by_id.get(leaders.get(key))
		pemimpin.append({'label': name, 'nome': m.nome if m else None, 'idade': m.age() if m else None})
	context = {
		'group': group, 'village': village, 'tot': tot, 'rows': rows, 'pemimpin': pemimpin,
		'title': f'Suku {village.name}', 'legend': f'Suku {village.name}',
		'meta_description': f'Lista membru suku {village.name}, Partido Democratico, Postu Dom Aleixo.',
	}
	return render(request, 'membro/suku_rekap.html', context)
