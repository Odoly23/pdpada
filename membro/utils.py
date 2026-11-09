import datetime
from django.db.models import Q
from membro.models import Membro, Historia, Alokasaun, POZISAUN_POR_NIVEL

SNAPSHOT_FIELDS = ['nome', 'sex', 'place_of_birth', 'date_of_birth', 'marital', 'nu_eleitoral',
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
	'marital': ['Solteiro/a', 'Casado/a', 'Divorciado/a', 'Viuvo/a'],
	'aprovasaun': ['Pendente', 'Aprovadu', 'Rejeitadu'],
	'status': ['Ativu', 'Inativu', 'Falesidu'],
	'sex': ['Mane', 'Feto'],
}
FILTER_IDS = ['village', 'aldeia', 'organizasaun']


def snapshot(membro):
	"""Foto kondisaun data membru (label -> teks) untuk bandingan sebelum/depois edit."""
	data = {}
	for name in SNAPSHOT_FIELDS:
		field = Membro._meta.get_field(name)
		val = getattr(membro, name)
		if name in ('image', 'file_eleitoral'):
			val = ('iha …' + val.name.rsplit('/', 1)[-1][:8]) if val else None  # nama file = hash, tampilkan ringkas
		data[str(field.verbose_name)] = '-' if val in (None, '') else str(val)
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
	if params.get('nivel') in POZISAUN_POR_NIVEL:
		qs = qs.filter(nivel=params['nivel'])
	if params.get('pozisaun') in ('Presidente', 'Coordenador', 'Sekretariu'):
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
	return qs
