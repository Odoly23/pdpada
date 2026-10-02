"""
Definisaun RBAC: papel (= Django Group) no matriks permisaun.

Papel = Group. Permisaun = Django Permission (codename). Tabela ida de'it ne'e
mak sai fonte lolos; `python manage.py seed_rbac` (no post_migrate) sinkroniza ba database.
"""

ADMIN = 'admin'
PRESIDENTE = 'presidente'
OPD = 'opd'
OMD = 'omd'
DPD = 'dpd'
POSTU = 'postu'
SUKU = 'suku'
ALDEIA = 'aldeia'

# Ordem prioridade (kuaoin = prioridade as). Atu user ho grupu barak, papel determinístiku.
ROLE_PRIORITY = [ADMIN, PRESIDENTE, POSTU, SUKU, ALDEIA, OPD, OMD, DPD]

ROLE_LABELS = {
    ADMIN: 'Admin Sistema',
    PRESIDENTE: 'Presidente PADA',
    OPD: 'OPD',
    OMD: 'OMD',
    DPD: 'DPD',
    POSTU: 'Coordenador Postu',
    SUKU: 'Coordenador Suku',
    ALDEIA: 'Coordenador Aldeia',
}

# Papel ne'ebé hetan eskopu husi organizasaun (OPD/OMD/DPD)
ORG_ROLES = (OPD, OMD, DPD)
# Papel ne'ebé hetan eskopu husi wilayah
TERRITORIAL_ROLES = (POSTU, SUKU, ALDEIA)
# Papel ne'ebé haree dadus hotu
GLOBAL_ROLES = (ADMIN, PRESIDENTE)

ROLE_CHOICES = [(r, ROLE_LABELS[r]) for r in ROLE_PRIORITY]

# codename permisaun -> (app_label, model) ba verifikasaun
ALL_PERMS = [
    'membro.view_membru', 'membro.add_membru', 'membro.change_membru', 'membro.delete_membru',
    'membro.confirm_membru', 'membro.approve_membru', 'membro.view_report',
    'membro.view_kargu', 'membro.add_kargu', 'membro.change_kargu', 'membro.delete_kargu',
    'membro.view_organizasaun', 'membro.add_organizasaun', 'membro.change_organizasaun',
    'users.manage_users',
    'config.view_auditlog',
]

ROLE_PERMISSIONS = {
    # Input membru = Aldeia de'it (rekizitu partidu); Admin bele korrije/hamoos, la input.
    ADMIN: [p for p in ALL_PERMS if p != 'membro.add_membru'],
    PRESIDENTE: ['membro.view_membru', 'membro.view_report', 'membro.view_kargu',
                 'membro.view_organizasaun'],
    OPD: ['membro.view_membru', 'membro.view_report'],
    OMD: ['membro.view_membru', 'membro.view_report'],
    DPD: ['membro.view_membru', 'membro.view_report'],
    POSTU: ['membro.view_membru', 'membro.approve_membru', 'membro.view_report',
            'membro.view_kargu'],
    SUKU: ['membro.view_membru', 'membro.confirm_membru', 'membro.view_report',
           'membro.view_kargu'],
    # Aldeia de'it mak bele input membru (rekizitu partidu).
    ALDEIA: ['membro.view_membru', 'membro.add_membru', 'membro.change_membru',
             'membro.view_report', 'membro.view_kargu'],
}
