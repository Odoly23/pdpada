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

Pembaruan di server: `bash update.sh` (git pull, pip, **migrate**, collectstatic, check), lalu Reload.

Setelah login sebagai `admin`: isi **Data Master** (Suku dan Aldeia di Postu Dom Aleixo, nama lengkap Organizasaun), lalu buat **Uzuáriu** untuk tiap peran.

Deploy ke PythonAnywhere: lihat [`docs/DEPLOY_PYTHONANYWHERE.md`](docs/DEPLOY_PYTHONANYWHERE.md). Data demo fiktif untuk presentasi: `python manage.py seed_demo --password '...'` (hapus dengan `--hapus`).

## Fitur utama

- **Varanda** (beranda): hero dengan bendera utuh, pencarian cepat, dan kartu pintasan sesuai peran. **Painel** (`/membro/painel/`): banner peran, tabel matriks bertaut, dan grafik.
- **Pesquiza**: cari membru berdasarkan nama, Nu. Eleitoral, atau telepon, dengan saran otomatis; hanya dalam wilayah user.
- **Ekspor CSV penuh** (peran Postu): sesuai filter dan wilayah, aman dari formula injection, tercatat di Historia.
- **Dupla Potensial** (Presidente/Coordenador Postu): nama + tanggal lahir sama, atau nomor telepon sama.
- **Backup** (`python manage.py backup_data`), **health check** (`/healthz/`), batas percobaan login, log berputar.
- Database: indeks sesuai query nyata dan `CheckConstraint` untuk nilai pilihan. Lihat [`docs/MAINTENANCE.md`](docs/MAINTENANCE.md).

## Struktur

| App | Isi |
|---|---|
| `main` | layout (topbar, navbar, sidebar mobile, footer), login/logout, home, static |
| `custom` | data master: Municipality, AdministrativePost, Village (Suku), Aldeia, Organizasaun, Year + dropdown AJAX |
| `config` | `utils` (hash), `decorators` (`allowed_users`), `roles`, `user_utils` (scope), upload, command `seed_inisial` |
| `users` | `UserScope` (wilayah user), kelola uzuáriu (Admin) |
| `membro` | `Membro`, `Alokasaun` (posisi/kargu), `Historia` (log perubahan); views, forms, urls |
| `notification` | notifikasi lonceng (API DRF `/api/notification/...`, polling 5 detik): approver = membru Pendente, sekjer = membru Rejeitadu |
| `report` | relatoriu tabular (`/report/`) dan grafiku (`/report/chart/`), menu dropdown *Relatoriu*, grafik Highcharts (`/report/chart/`) + API (`/report/api/...`) |

## Tampilan

`main/static/main/css/main.css` memuat variabel warna (`--navy`, `--navy-dk`) di bagian atas. Menu navbar desktop dan sidebar mobile berasal dari satu definisi per peran di `config/context_processors.py`. Varanda (home) menampilkan banner peran, bar tombol, tabel matriks bertaut (Suku/Aldeia/Organizasaun sesuai peran) dan grafik. Semua grafik memakai Highcharts `styledMode` (halaman Grafik berisi 9 grafik); warna di `main/static/main/js_custom/chart.css` (`--highcharts-color-N`). Ekspor grafik berjalan offline (tanpa server Highcharts).

## Peran dan hak akses

| Peran (group) | Lihat data | Input/edit | Aprova/rejeita | Lainnya |
|---|---|---|---|---|
| `presidente` | semua | – | ya | aloka pozisaun, hamoos membru, lihat historia |
| `koord_postu` | semua | – | ya | hamoos membru, lihat historia |
| `sekr_postu` | semua | – | – | – |
| `koord_suku` / `sekr_suku` | sukunya | sekr_suku | – | – |
| `koord_aldeia` / `sekr_aldeia` | aldeianya | sekr_aldeia | – | – |
| `koord_org` | anggota organisasinya | – | – | – |
| `sekr_org` (Sekretariu OJD/OPD/MPD/organisasi lain) | anggota organisasinya | ya (organisasi terkunci ke organisasinya, suku/aldeia bebas di Postu) | – | – |
| `admin` | tidak melihat data membru | – | – | uzuáriu, data master, tinan ativu, historia |

**Notifikasi:** lonceng di navbar menampilkan badge jumlah *Hein Aprovasaun* (Presidente/Coordenador Postu) atau *Membru Rejeitadu* (Sekjer Suku/Aldeia) dan diperbarui otomatis tiap 5 detik.

**Dashboard Struktura** (`/membro/alokasaun/dash/`): pemegang posisi Postu, Suku, Aldeia, Organizasaun yang aktif, kelengkapan aldeia (mis. 2/3 punya Coordenador), tautan ke daftar terfilter, dan grafik.

**Upload dan keamanan file:** foto (JPEG/PNG, maks. 2 MB) dan kartu eleitoral (PDF, maks. 5 MB) diperiksa **isinya**, bukan hanya ekstensi. Foto didekode lalu dienkode ulang sebagai JPEG baru (EXIF dan data tambahan terbuang, maks. 1600 px). PDF harus valid, tidak terenkripsi, maks. 20 halaman, dan tanpa JavaScript, lampiran, atau aksi peluncuran. Nama file selalu dibuat baru: HMAC-SHA256 dari token acak (64 hex). File disimpan di folder privat `private/` (bukan `media/`), tidak punya URL publik, dan hanya bisa dibuka lewat `/membro/<hashid>/file/<foto|eleitoral>/` oleh user yang berhak melihat membru tersebut. Pembukaan PDF eleitoral tercatat di Historia. Field No. BI sudah dihapus; identitas pemilih memakai Nu. Eleitoral.

Alur: sekretaris suku/aldeia input → status **Pendente** → Presidente atau Coordenador Postu **Aprova** atau **Rejeita** (wajib isi razaun). Data yang diedit (juga yang sudah Aprovadu) kembali **Pendente**. Setiap kria/edita/aprova/rejeita/aloka/hamoos tercatat di **Historia**.

Satu membru = satu Nu. Eleitoral (unik) dan satu organisasi. Nu. Eleitoral ganda ditolak dengan notifikasi *DUPLIKADU*; nama + data moris yang sama memunculkan peringatan.

Daftar dan laporan menampilkan **tinan ativu** (ubah di Data Master → Tinan); daftar membru punya tautan "Tinan hotu".

## Tes

```bash
python manage.py test
```
