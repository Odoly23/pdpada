ADMIN = 'admin'
PRESIDENTE = 'presidente'
KOORD_POSTU = 'koord_postu'
SEKR_POSTU = 'sekr_postu'
KOORD_SUKU = 'koord_suku'
SEKR_SUKU = 'sekr_suku'
KOORD_ALDEIA = 'koord_aldeia'
SEKR_ALDEIA = 'sekr_aldeia'
KOORD_ORG = 'koord_org'
SEKR_ORG = 'sekr_org'

ROLE_LABELS = [
	(PRESIDENTE, 'Presidente Postu'),
	(KOORD_POSTU, 'Coordenador Postu'),
	(SEKR_POSTU, 'Sekretariu Postu'),
	(KOORD_SUKU, 'Coordenador Suku'),
	(SEKR_SUKU, 'Sekjer Suku'),
	(KOORD_ALDEIA, 'Coordenador Aldeia'),
	(SEKR_ALDEIA, 'Sekjer Aldeia'),
	(KOORD_ORG, 'Coordenador Organizasaun'),
	(SEKR_ORG, 'Sekretariu Organizasaun'),
	(ADMIN, 'Admin'),
]

POSTU_ROLES = [PRESIDENTE, KOORD_POSTU, SEKR_POSTU]
SUKU_ROLES = [KOORD_SUKU, SEKR_SUKU]
ALDEIA_ROLES = [KOORD_ALDEIA, SEKR_ALDEIA]
ORG_ROLES = [KOORD_ORG, SEKR_ORG]

# Hak akses
INPUT_ROLES = [SEKR_SUKU, SEKR_ALDEIA]            # input dan edit data membru
APROVA_ROLES = [PRESIDENTE, KOORD_POSTU]          # aprova atau rejeita
ALOKA_ROLES = [PRESIDENTE]                        # aloka pozisaun (coordenador, dll)
HISTORIA_ROLES = [ADMIN, PRESIDENTE, KOORD_POSTU]  # lee historia mudansa data
VIEW_ROLES = POSTU_ROLES + SUKU_ROLES + ALDEIA_ROLES + ORG_ROLES
