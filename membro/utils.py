import datetime
import re
from functools import reduce
from operator import and_
from django.db.models import Count, Q
from urllib.parse import urlencode
from config.user_utils import membro_scope
from custom.models import Year
from membro.models import Membro, Historia, Alokasaun, Servisu, Pozisaun, NIVEL

SNAPSHOT_FIELDS = ['kategoria', 'nome', 'sex', 'place_of_birth', 'date_of_birth', 'marital', 'nu_eleitoral',
	'telefone', 'image', 'file_eleitoral', 'village', 'aldeia', 'address', 'organizasaun', 'data_hakbit', 'status']

AGE_BINS = [(0, 17, '< 18'), (18, 25, '18-25'), (26, 35, '26-35'), (36, 45, '36-45'),
	(46, 55, '46-55'), (56, 65, '56-65'), (66, 200, '> 65')]
AGE_RANGE = {label: (lo, hi) for lo, hi, label in AGE_BINS}


def years_ago(today, n):
	try:
		return today.replace(year=today.year - n)
	except ValueError:  # 29 Februari
		return today.replace(year=today.year - n, day=28)


FILTER_CHOICES = {
	'marital': ['Klosan', "Kaben-na'in", 'Fahe malu', 'Faluk'],
	'aprovasaun': ['Pendente', 'Aprovadu', 'Rejeitadu'],
	'status': ['Ativu', 'Inativu', 'Falesidu'],
	'sex': ['Mane', 'Feto'],
}
FILTER_IDS = ['village', 'aldeia', 'organizasaun']


def filter_jenis(qs, jenis):
	"""Struktura = iha pozisaun ativu; Militante (Militante & Simpatizante) = membru seluk ne'ebé la iha pozisaun.
	'Simpatizante' (ligasaun tuan) hanesan ho 'Militante'."""
	if jenis == 'Struktura':
		return qs.filter(is_colocado=True)
	if jenis in ('Militante', 'Simpatizante'):
		return qs.filter(is_colocado=False)
	return qs


def snapshot(membro):
	"""Foto kondisaun data membru (label -> teks) untuk bandingan sebelum/depois edit."""
	data = {}
	for name in SNAPSHOT_FIELDS:
		field = Membro._meta.get_field(name)
		val = getattr(membro, name)
		if name in ('image', 'file_eleitoral'):
			val = ('iha …' + val.name.rsplit('/', 1)[-1][:8]) if val else None  # nama file = hash, tampilkan ringkas
		data[str(field.verbose_name)] = '-' if val in (None, '') else str(val)
	sv = Servisu.objects.filter(membro=membro).first() if membro.pk else None
	data['Servisu'] = sv.resumu() if sv else '-'
	return data


def diff_snapshot(old, new):
	lines = [f'{k}: {old[k]} -> {new[k]}' for k in new if old.get(k) != new[k]]
	return '\n'.join(lines)


def log_historia(user, membro, aksaun, detalhe='', nome=None):
	return Historia.objects.create(
		membro=membro, membro_nome=nome or (str(membro) if membro else ''),
		aksaun=aksaun, detalhe=detalhe, user=user)


def apply_filters(qs, params):
	"""Filter lista membru dari parameter GET; nilai tidak valid diabaikan."""
	for key, allowed in FILTER_CHOICES.items():
		val = params.get(key)
		if val in allowed:
			qs = qs.filter(**{key: val})
	for key in FILTER_IDS:
		val = params.get(key)
		if val and val.isdigit():
			if key == 'organizasaun' and int(val) == 0:  # 0 = membru laiha organizasaun
				qs = qs.filter(organizasaun__isnull=True)
			else:
				qs = qs.filter(**{f'{key}_id': int(val)})
	if params.get('marital') == 'laiha':
		qs = qs.filter(Q(marital__isnull=True) | Q(marital=''))
	qs = filter_jenis(qs, params.get('jenis'))
	if params.get('servisu') in ('Servisu', 'Seidauk'):
		qs = qs.filter(servisu__status=params['servisu'])
	elif params.get('servisu') == 'laiha':
		qs = qs.filter(servisu__isnull=True)
	if params.get('setor') in ('Governu', 'Organizasaun', 'Kompania'):
		qs = qs.filter(servisu__setor=params['setor'])
	umur = params.get('umur')
	if umur in AGE_RANGE:
		lo, hi = AGE_RANGE[umur]
		today = datetime.date.today()
		qs = qs.filter(date_of_birth__lte=years_ago(today, lo), date_of_birth__gt=years_ago(today, hi + 1))
	hakbit = params.get('hakbit')
	if hakbit and hakbit.isdigit():
		qs = qs.filter(data_hakbit__year=int(hakbit))
	return qs


def apply_alokasaun_filters(qs, params):
	"""Filter daftar alokasaun dari parameter GET (dipakai tautan di dashboard Struktura)."""
	if params.get('nivel') in dict(NIVEL):
		qs = qs.filter(nivel=params['nivel'])
	if params.get('pozisaun') and Pozisaun.objects.filter(naran=params['pozisaun']).exists():
		qs = qs.filter(pozisaun=params['pozisaun'])
	if params.get('ativu') in ('Sim', 'Lae'):
		qs = qs.filter(ativu=params['ativu'])
	village = params.get('village')
	if village and village.isdigit():
		qs = qs.filter(Q(village_id=int(village)) | Q(aldeia__village_id=int(village)))
	for key in ('aldeia', 'organizasaun'):
		val = params.get(key)
		if val and val.isdigit():
			qs = qs.filter(**{f'{key}_id': int(val)})
	organ = params.get('organ')  # Ejekutivu = la iha organizasaun; kódigu (OJD, OMD, MPD...) = sayap
	if organ == 'Ejekutivu':
		qs = qs.filter(organizasaun__isnull=True)
	elif organ:
		qs = qs.filter(organizasaun__code=organ)
	return qs


def membro_listing(user, params):
	"""Queryset daftar membru untuk user: wilayah + tinan ativu (kecuali ano=hotu) + filter GET.
	Dipakai bersama oleh daftar dan ekspor CSV agar keduanya selalu sama."""
	qs = membro_scope(user).select_related('village', 'aldeia', 'organizasaun', 'servisu')
	ano = Year.objects.filter(is_active=True).first()
	semua_ano = params.get('ano') == 'hotu'
	if ano and not semua_ano:
		qs = qs.filter(year=ano)
	return apply_filters(qs, params), semua_ano


SEARCH_MIN = 2


def search_membro(user, q, limit=50):
	"""Cari membru dalam wilayah user: semua kata ada di naran, awalan Nu. Eleitoral, atau Nu. Telemóvel."""
	q = ' '.join((q or '').split())
	if len(q) < SEARCH_MIN:
		return Membro.objects.none()
	cond = reduce(and_, [Q(nome__icontains=word) for word in q.split()])
	cond |= Q(nu_eleitoral__istartswith=q)
	digits = re.sub(r'\D', '', q)
	if digits.startswith('670') and len(digits) > 9:  # nomor disimpan tanpa kode negara (+670)
		digits = digits[3:]
	if len(digits) >= 6:
		cond |= Q(telefone__contains=digits)
	return membro_scope(user).filter(cond).select_related('village', 'aldeia', 'organizasaun').order_by('nome')[:limit]


CSV_HEADER = ['Nu. Eleitoral', 'Naran', 'Sexu', 'Data Moris', 'Idade', 'Estadu Sivíl', 'Nu. Telemóvel', 'Suku', 'Aldeia',
	'Hela Fatin', 'Organizasaun', 'Data Hakbit', 'Status', 'Aprovasaun', 'Tinan', 'Kategoria', 'Servisu']


def csv_safe(value):
	"""Cegah CSV/formula injection: sel berawalan = + - @ dianggap rumus oleh Excel."""
	text = '' if value is None else str(value)
	return "'" + text if text[:1] in ('=', '+', '-', '@', '\t', '\r') else text


def servisu_text(m):
	sv = getattr(m, 'servisu', None) if hasattr(m, 'servisu') else None
	return sv.resumu() if sv else ''


def csv_row(m):
	return [csv_safe(v) for v in (
		m.nu_eleitoral, m.nome, m.sex, m.date_of_birth, m.age(), m.marital or '', m.telefone or '', m.village, m.aldeia,
		m.address or '', m.organizasaun or '', m.data_hakbit or '', m.status, m.aprovasaun, m.year or '', m.jenis_label(), servisu_text(m))]
