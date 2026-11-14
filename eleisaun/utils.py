from collections import defaultdict
from django.db.models import Count
from django.utils import timezone
from custom.models import Village, Year
from eleisaun.models import Eleisaun, TempatVoting, Resultado
from membro.models import Membro


def eleisaun_ativu():
	return Eleisaun.objects.filter(ativu=True).first()


def _membro_qs():
	"""Membru tinan ativu (sama dengan total di Varanda); tanpa tinan ativu: semua."""
	ano = Year.objects.filter(is_active=True).first()
	return Membro.objects.filter(year=ano) if ano else Membro.objects.all()


def kompara(votos, membru):
	"""Label perbandingan votu PD dengan total membru (Tetun INL): menus, liu, atau hanesan."""
	if votos < membru:
		return {'kode': 'menus', 'label': 'Menus husi total dadus', 'diferensa': votos - membru}
	if votos > membru:
		return {'kode': 'liu', 'label': 'Liu total dadus', 'diferensa': votos - membru}
	return {'kode': 'hanesan', 'label': 'Hanesan ho total dadus', 'diferensa': 0}


def persen(a, b):
	return round(a * 100 / b, 1) if b else 0


def live_payload():
	"""Data dashboard live: hanya angka agregat dan nama tempat (tanpa data pribadi)."""
	el = eleisaun_ativu()
	if not el:
		return {'ativu': False}
	tempat = list(TempatVoting.objects.filter(ativu=True).select_related('village'))
	hasil = {r.tempat_id: r for r in Resultado.objects.filter(eleisaun=el, submetidu=True)}
	rows, votos, submetidu = [], 0, 0
	for t in tempat:
		r = hasil.get(t.pk)
		v = r.votos_partidu if r else 0
		votos += v
		submetidu += 1 if r else 0
		rows.append({'tempat': t.naran, 'suku': t.village.name, 'votos': v, 'submetidu': bool(r),
			'oras': timezone.localtime(r.submetidu_em).strftime('%H:%M') if r and r.submetidu_em else ''})
	membru = _membro_qs().count()
	return {
		'ativu': True, 'eleisaun': el.naran, 'tinan': el.tinan, 'atualizadu': timezone.localtime().strftime('%H:%M:%S'),
		'kpi': {'votos': votos, 'membru': membru, 'persentajen': persen(votos, membru), 'submetidu': submetidu, 'tempat': len(rows),
			'kompara': kompara(votos, membru)},
		'tempat': rows,
	}


def komparasaun_data():
	"""Perbandingan total membru dan total votu PD per suku (hanya hasil yang sudah disubmit)."""
	el = eleisaun_ativu()
	membru = dict(_membro_qs().order_by().values_list('village_id').annotate(n=Count('id')))
	tempat_total, tempat_sub, votos = defaultdict(int), defaultdict(int), defaultdict(int)
	tempat_suku = {}
	for t in TempatVoting.objects.filter(ativu=True):
		tempat_total[t.village_id] += 1
		tempat_suku[t.pk] = t.village_id
	if el:
		for r in Resultado.objects.filter(eleisaun=el, submetidu=True):
			vid = tempat_suku.get(r.tempat_id)
			if vid is not None:
				votos[vid] += r.votos_partidu
				tempat_sub[vid] += 1
	rows = []
	for v in Village.objects.order_by('name'):
		m, vt = membru.get(v.pk, 0), votos.get(v.pk, 0)
		rows.append({'suku': v.name, 'membru': m, 'votos': vt, 'persentajen': persen(vt, m), 'kompara': kompara(vt, m),
			'tempat': tempat_total.get(v.pk, 0), 'submetidu': tempat_sub.get(v.pk, 0)})
	tm, tv = sum(r['membru'] for r in rows), sum(r['votos'] for r in rows)
	totals = {'membru': tm, 'votos': tv, 'persentajen': persen(tv, tm), 'diferensa': tv - tm, 'kompara': kompara(tv, tm),
		'tempat': sum(r['tempat'] for r in rows), 'submetidu': sum(r['submetidu'] for r in rows)}
	return el, rows, totals
