from django.db.models import Count, Q

COUNT_KEYS = ('total', 'mane', 'feto', 'aprovadu', 'pendente', 'rejeitadu')


def matrix_rows(qs, id_field, name_field, none_label='Laiha organizasaun'):
	"""Rekap membru per unit: total, sexu, dan status aprovasaun (satu query)."""
	rows = qs.values(id_field, name_field).annotate(
		total=Count('id'),
		mane=Count('id', filter=Q(sex='Mane')),
		feto=Count('id', filter=Q(sex='Feto')),
		aprovadu=Count('id', filter=Q(aprovasaun='Aprovadu')),
		pendente=Count('id', filter=Q(aprovasaun='Pendente')),
		rejeitadu=Count('id', filter=Q(aprovasaun='Rejeitadu')),
	).order_by(name_field)
	return [dict({'id': r[id_field] or 0, 'name': r[name_field] or none_label}, **{k: r[k] for k in COUNT_KEYS}) for r in rows]
