"""Template struktur PD (Suku, Aldeia, dan sayap OJD/OMD/MPD) sesuai dokumen resmi PD.

Urutan baris sama dengan dokumen. Setiap seksaun punya satu Chefe (unik) dan satu baris Membru
(bisa banyak orang). Label `(PD)` di dokumen diganti kode organisasi untuk sayap (mis. OMD).
"""

SEKSAUN = ['Politika e Programa', 'Agitasaun e Propaganda', 'Sosiais e Kultura',
	'Mobilizasaun da Massa', 'Logistika e Transporte']

# (naran di tabela Pozisaun, label di dokumen)
PD_TEMPLATE = [
	('Coordenador', 'Coordenador (PD)'),
	('Vice Coordenador I', '1º Vice Coordenador'),
	('Vice Coordenador II', '2º Vice Coordenador'),
	('Sekretariu', 'Secretario (PD)'),
	('Vice Sekretariu I', '1º Vice Secretario'),
	('Vice Sekretariu II', '2º Vice Secretario'),
	('Tezoureiru', 'Tezoureiro/a'),
]
for _s in SEKSAUN:
	PD_TEMPLATE.append((f'Chefe Seksaun {_s}', f'Chefe Seksaun {_s}'))
	PD_TEMPLATE.append((f'Membru Seksaun {_s}', 'Membros'))

# sayap organisasi: OJD, OMD, MPD (sama dengan template, label (PD) -> (KODE))
SAYAP_CODES = ('OJD', 'OMD', 'MPD')


def label_unit(label, org_code=None):
	"""Label baris untuk unit: sayap organisasi mengganti (PD) dengan kode organisasi."""
	return label.replace('(PD)', f'({org_code})') if org_code else label


def template_naran():
	return [naran for naran, _ in PD_TEMPLATE]


def is_membru(naran):
	return naran.startswith('Membru Seksaun ')
