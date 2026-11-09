from membro.models import Membro, Historia

SNAPSHOT_FIELDS = ['nome', 'sex', 'place_of_birth', 'date_of_birth', 'marital', 'nu_eleitoral', 'nu_bi',
	'telefone', 'image', 'village', 'aldeia', 'address', 'organizasaun', 'data_hakbit', 'status']

FILTER_CHOICES = {
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
		if name == 'image':
			val = val.name if val else None
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
			qs = qs.filter(**{f'{key}_id': int(val)})
	hakbit = params.get('hakbit')
	if hakbit and hakbit.isdigit():
		qs = qs.filter(data_hakbit__year=int(hakbit))
	return qs
