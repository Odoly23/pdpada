"""Data Lista Delegadu suku: pemimpin suku dan delegadu tiap aldeia (Koord/Sekretario + sayap organisasi)."""
from collections import defaultdict
from django.db.models import Q
from custom.models import Aldeia
from membro.models import Alokasaun

POS = {'Coordenador': 'Koord', 'Sekretariu': 'Sekretario', 'Presidente': 'Presidente'}
POS_ORDER = {'Coordenador': 0, 'Sekretariu': 1}


def pozisaun_label(a):
	"""Contoh: Koord Suku, Sekretario Suku, Koord OJD Suku, Koord Aldeia, Koord OJD."""
	pos = POS.get(a.pozisaun, a.pozisaun)
	code = a.organizasaun.code if a.organizasaun_id else ''
	if a.nivel == 'Suku':
		return f'{pos} {code} Suku' if code else f'{pos} Suku'
	return f'{pos} {code}' if code else f'{pos} Aldeia'


def _row(a):
	m = a.membro
	return {
		'nome': m.nome, 'pozisaun': pozisaun_label(a), 'aldeia': m.aldeia.name, 'eleitoral': m.nu_eleitoral or '',
		'hp': m.telefone or '', 'utama': not a.organizasaun_id,  # pemimpin utama dicetak tebal
		'sort': (1 if a.organizasaun_id else 0, POS_ORDER.get(a.pozisaun, 9), a.organizasaun.code if a.organizasaun_id else ''),
	}


def delegadu_data(village):
	"""{'village', 'n_aldeia', 'suku_rows', 'blocks': [{'aldeia', 'rows', 'hp'}]} untuk satu suku."""
	allocs = Alokasaun.objects.filter(ativu='Sim', pozisaun__in=list(POS_ORDER)).filter(
		Q(nivel='Suku', village=village) | Q(nivel='Aldeia', aldeia__village=village)
	).select_related('membro', 'membro__aldeia', 'aldeia', 'organizasaun')
	suku_rows, per_aldeia = [], defaultdict(list)
	for a in allocs:
		if a.nivel == 'Suku':
			suku_rows.append(_row(a))
		else:
			per_aldeia[a.aldeia_id].append(_row(a))
	suku_rows.sort(key=lambda r: r['sort'])
	aldeias = list(Aldeia.objects.filter(village=village))
	blocks = []
	for ald in aldeias:
		rows = sorted(per_aldeia.get(ald.pk, []), key=lambda r: r['sort'])
		hp = next((r['hp'] for r in rows if r['utama'] and r['hp']), '') or next((r['hp'] for r in rows if r['hp']), '')
		blocks.append({'aldeia': ald.name, 'rows': rows, 'hp': hp})
	n_delegadu = len(suku_rows) + sum(len(b['rows']) for b in blocks)
	return {'village': village, 'n_aldeia': len(aldeias), 'n_delegadu': n_delegadu, 'suku_rows': suku_rows, 'blocks': blocks}
