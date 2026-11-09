# Deploy SGDM-PDPADA di PythonAnywhere

Ganti `USERNAME` dengan username PythonAnywhere Anda. Akun gratis cukup (SQLite, satu web app di `USERNAME.pythonanywhere.com`).

## 1. Ambil kode dan siapkan environment (tab **Consoles** → Bash)

```bash
cd ~
git clone https://github.com/Odoly23/pdpada.git
cd pdpada
git checkout main        # jika PR belum di-merge: git checkout claude/sleepy-edison-nntjc1
mkvirtualenv --python=/usr/bin/python3.12 pdpada-venv
pip install -r requirements.txt
```

> Repo privat? Unggah zip lewat tab **Files** lalu `unzip`, atau jadikan repo publik sementara.

## 2. Isi `.env`

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(60))"   # salin hasilnya
nano .env
```

Isi minimal (ganti nilainya):

```
DJANGO_SECRET_KEY=<hasil perintah di atas>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=USERNAME.pythonanywhere.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://USERNAME.pythonanywhere.com
DB_ENGINE=sqlite
ADMIN_PASSWORD=<password admin yang Anda pilih, minimal 10 karakter>
```

> Jangan ganti `DJANGO_SECRET_KEY` setelah ada data (hashid di URL dihitung dari kunci ini).

## 3. Database dan static

```bash
python manage.py migrate
python manage.py seed_inisial          # peran, Dili/Dom Aleixo, OJD/OPD/MPD, tinan ativu, user admin
python manage.py collectstatic --noinput
```

### Data demo untuk presentasi (opsional, FIKTIF)

```bash
python manage.py seed_demo --password 'PasswordDemoYangKuat2026!'
```

Membuat 3 suku, 9 aldeia, 60 membru fiktif, dan 8 user: `demo_presidente`, `demo_koordpostu`, `demo_sekrpostu`, `demo_koordsuku`, `demo_sekrsuku`, `demo_sekraldeia`, `demo_koordorg`, `demo_sekrorg` (semua memakai password di atas). Hapus semuanya sebelum dipakai sungguhan:

```bash
python manage.py seed_demo --hapus
```

## 4. Web app (tab **Web**)

1. **Add a new web app** → **Manual configuration** → Python **3.12**.
2. **Source code** dan **Working directory**: `/home/USERNAME/pdpada`
3. **Virtualenv**: `/home/USERNAME/.virtualenvs/pdpada-venv`
4. Klik link **WSGI configuration file**, hapus isinya, ganti dengan:

```python
import os
import sys

path = '/home/USERNAME/pdpada'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'pdpada.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

5. **Static files** (tambah dua baris):

| URL | Directory |
|---|---|
| `/static/` | `/home/USERNAME/pdpada/staticfiles` |
| `/media/` | `/home/USERNAME/pdpada/media` (opsional; foto dan PDF eleitoral kini ada di folder privat `private/`, jangan dipetakan) |

6. Aktifkan **Force HTTPS**.
7. Klik **Reload**, lalu buka `https://USERNAME.pythonanywhere.com`.

## 5. Cek cepat

- Login `admin` (password dari `ADMIN_PASSWORD`) → menu Data Master, Uzuáriu, Historia.
- Login `demo_presidente` → Home berisi grafik, menu Aprovasaun, Struktura.
- Login `demo_sekrsuku` → Aumenta Membru (suku terkunci ke Suku Demo 1).

## 6. Jika ada masalah (tab **Web** → *Error log*)

| Gejala | Penyebab / solusi |
|---|---|
| `DisallowedHost` / Bad Request (400) | `DJANGO_ALLOWED_HOSTS` salah di `.env` |
| `CSRF verification failed` (403) saat login | isi `DJANGO_CSRF_TRUSTED_ORIGINS=https://USERNAME.pythonanywhere.com` |
| Halaman tanpa gaya/ikon/grafik | jalankan `collectstatic`, cek pemetaan `/static/` |
| Foto/PDF membru tidak muncul | file disajikan lewat halaman ber-login dari folder `private/`; cek folder itu ada dan dapat ditulis (`ls -la ~/pdpada/private`) |
| `ModuleNotFoundError` | path virtualenv di tab Web salah |
| `OperationalError: no such column ...` / `no such table ...` | **migrasi belum dijalankan** setelah `git pull`: `workon Env && python manage.py migrate`, lalu Reload (atau jalankan `bash update.sh`) |
| `RuntimeError: DJANGO_SECRET_KEY wajib diisi` | `.env` belum terisi atau tidak di `/home/USERNAME/pdpada/.env` |

Setiap mengubah kode atau `.env`: klik **Reload**.

## 7. Update versi baru

Cara termudah (menjalankan semua langkah yang sering terlupa: kode, paket, **migrasi**, static, pengecekan):

```bash
cd ~/pdpada
workon Env
bash update.sh
```

lalu klik **Reload** di tab Web. Cara manual:

```bash
cd ~/pdpada && git pull
workon Env
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

> Setiap pembaruan bisa membawa migrasi baru. Jika `migrate` terlewat, halaman akan menampilkan `no such column`.

## Catatan akun gratis

- Web app harus diperpanjang dengan tombol **Run until...** di tab Web (jadwal sekitar tiap 3 bulan).
- Cadangan data: unduh `~/pdpada/db.sqlite3` dan folder `~/pdpada/private/` (foto dan kartu eleitoral) lewat tab **Files**.
