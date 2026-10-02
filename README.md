# PDPADA — Sistema Jestaun Membru Partidu

Django 5.2 LTS · SQLite · RBAC (Group) · django-axes · Argon2 · DRF (sesaun de'it)

## Estrutura

```
pdpada/    settings, urls
config/    RBAC (roles.py), eskopu (scope.py), decorators, audit log, testing helper
custom/    BaseModel (soft-delete + audit field) · Munisípiu → Postu → Suku → Aldeia
users/     Profile (eskopu user), login/logout, jestaun user (admin), troka password, audit
membro/    Membru · Kargu (Coordenador/Sekjen) · Organizasaun (OPD/OMD/DPD) · fluxu aprovasaun
report/    dashboard + API (eskopu tuir papel)
main/      layout, home, error page, static (vendor local)
```

## Papel (RBAC = Django Group)

| Papel | Haree | Bele |
|---|---|---|
| `admin` | hotu | jere user, kargu, korrije/hamoos membru, audit log (la input membru) |
| `presidente` | hotu | haree de'it |
| `postu` | postu nian | **aprova** membru ne'ebé konfirma ona |
| `suku` | suku nian | **konfirma** membru |
| `aldeia` | aldeia nian | **input & edita** membru (de'it molok konfirma) |
| `opd` / `omd` / `dpd` | membru organizasaun nian | haree de'it |

Matriks permisaun iha `config/roles.py` (fonte úniku). `manage.py seed_rbac` (no `post_migrate`) sinkroniza.
Eskopu user iha `users.Profile` (postu/suku/aldeia/organizasaun). Dadus *sempre* filtra liu `config.scope.membru_queryset(user)`;
objetu por for a eskopu → **404**.

Fluxu membru: `Rejistadu (Aldeia) → Konfirmadu (Suku) → Aprovadu (Postu)`.

## Seguransa

- Password **Argon2**, minimu 12 karakter; la iha password default. Admin kria user → password aleatóriu hatudu dala ida, user *obrigadu* troka bainhira login.
- **django-axes**: bloku 1 oras depois tentativa sala 5× (username+IP). Admin bele hamoos bloku iha menu User.
- Sesaun 1 oras, cookie `Secure/HttpOnly/SameSite`, HSTS, SSL redirect, `X-Frame-Options: DENY` iha production.
- API: sesaun + CSRF de'it (la iha BasicAuth), permisaun `view_report`, throttle.
- Media (foto) **la publiku**: sirvi liu `membru-foto` ho verifikasaun login+eskopu.
- URL membru uza UUID (la ID sekuénsial). URL admin Django bele troka (`ADMIN_URL`).
- Audit log: login, login sala, bloku, kria/edita/konfirma/aprova/hamoos membru, jestaun user.
- Front-end vendor (Bootstrap, jQuery, DataTables, Chart.js) local, la depende CDN.

## Setup lokal

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # prense SECRET_KEY; DEBUG=True ba dezenvolvimentu
python manage.py migrate
python manage.py seed_geografia   # munisípiu 13
python manage.py createsuperuser  # superuser = papel admin
python manage.py runserver
python manage.py test
```

Postu/Suku/Aldeia: hatama liu husi `/<ADMIN_URL>/` (Django admin, superuser de'it). Depois kria user iha menu **User**.

## Production (Railway/VPS)

`build.sh` + `Procfile` prontu. Variavel obrigatóriu: `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DEBUG=False`.
**SQLite presiza volume persistente**: `SQLITE_PATH=/data/db.sqlite3`, `MEDIA_ROOT=/data/media`. Halo backup ba `/data` regularmente
(`sqlite3 db.sqlite3 ".backup backup.db"`). Se atrás proxy, define `AXES_PROXY_COUNT=1`.
