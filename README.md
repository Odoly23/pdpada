# SGDM-PDPADA

Sistema Jestaun Dadus Membru Partido Democratico (PD) — Postu Administrativu Dom Aleixo, Munisipiu Dili, Timor-Leste.

Django 5 + Django REST Framework + crispy-forms (Bootstrap 4). Semua aset frontend (Bootstrap, jQuery, DataTables, Font Awesome, Highcharts) ada di `main/static/main/` sehingga **berjalan offline**. Tampilan berbahasa Tetun.

## Menjalankan

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # isi DJANGO_SECRET_KEY (string acak panjang)
python manage.py migrate
python manage.py seed_inisial   # peran, Dili/Dom Aleixo, OJD/OPD/MPD, tinan ativu, user admin
python manage.py runserver
```

`seed_inisial` membuat user `admin`. Jika `ADMIN_PASSWORD` kosong di `.env`, password acak ditampilkan **sekali** di terminal.
Untuk MySQL: `DB_ENGINE=mysql` + `DB_*` di `.env` dan `pip install mysqlclient`.

> Jangan mengganti `DJANGO_SECRET_KEY` setelah ada data: kolom `hashed` (hashid di URL, HMAC-SHA256) dihitung dari kunci ini.

Setelah login sebagai `admin`: isi **Data Master** (Suku dan Aldeia di Postu Dom Aleixo, nama lengkap Organizasaun), lalu buat **Uzuáriu** untuk tiap peran.

## Struktur

| App | Isi |
|---|---|
| `main` | layout, navbar per peran, login/logout, home, static |
| `custom` | data master: Municipality, AdministrativePost, Village (Suku), Aldeia, Organizasaun, Year + dropdown AJAX |
| `config` | `utils` (hash), `decorators` (`allowed_users`), `roles`, `user_utils` (scope), upload, command `seed_inisial` |
| `users` | `UserScope` (wilayah user), kelola uzuáriu (Admin) |
| `membro` | `Membro`, `Alokasaun` (posisi/kargu), `Historia` (log perubahan); views, forms, urls |
| `report` | dashboard + API (`/report/api/...`) |

## Peran dan hak akses

| Peran (group) | Lihat data | Input/edit | Aprova/rejeita | Lainnya |
|---|---|---|---|---|
| `presidente` | semua | – | ya | aloka pozisaun, hamoos membru, lihat historia |
| `koord_postu` | semua | – | ya | hamoos membru, lihat historia |
| `sekr_postu` | semua | – | – | – |
| `koord_suku` / `sekr_suku` | sukunya | sekr_suku | – | – |
| `koord_aldeia` / `sekr_aldeia` | aldeianya | sekr_aldeia | – | – |
| `koord_org` / `sekr_org` | anggota organisasinya | – | – | – |
| `admin` | tidak melihat data membru | – | – | uzuáriu, data master, tinan ativu, historia |

Alur: sekretaris suku/aldeia input → status **Pendente** → Presidente atau Coordenador Postu **Aprova** atau **Rejeita** (wajib isi razaun). Data yang diedit (juga yang sudah Aprovadu) kembali **Pendente**. Setiap kria/edita/aprova/rejeita/aloka/hamoos tercatat di **Historia**.

Satu membru = satu Nu. Eleitoral (unik) dan satu organisasi. Nu. Eleitoral ganda ditolak dengan notifikasi *DUPLIKADU*; nama + data moris yang sama memunculkan peringatan.

Daftar dan laporan menampilkan **tinan ativu** (ubah di Data Master → Tinan); daftar membru punya tautan "Tinan hotu".

## Tes

```bash
python manage.py test
```
