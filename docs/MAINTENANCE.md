# Panduan Pemeliharaan SGDM-PDPADA (untuk 10 tahun ke depan)

Tujuan: siapa pun yang meneruskan sistem ini bisa memahami, memperbaiki, dan memperbarui tanpa menebak-nebak.

## 1. Peta kode (satu tanggung jawab per app)

| App | Tanggung jawab | Berkas utama |
|---|---|---|
| `config` | aturan lintas-app: peran (`roles.py`), cakupan wilayah (`user_utils.py`), decorator `allowed_users`, hash (`utils.py`), validasi file (`file_utils.py`), penyimpanan privat (`storage.py`), menu dan konteks (`context_processors.py`), perintah `seed_*` dan `backup_data` | `roles.py`, `user_utils.py` |
| `custom` | data master: Suku, Aldeia, Organizasaun, Tinan | `models.py` |
| `users` | akun, peran, wilayah user (`UserScope`), Painel Admin | `forms.py` |
| `membro` | inti: `Membro`, `Alokasaun`, `Historia`; daftar, form, approval, pencarian, ekspor, dobel, Painel | `models.py`, `views/`, `utils.py` |
| `report` | relatoriu tabular, grafiku, API angka | `views/view_1.py`, `api/` |
| `notification` | lonceng dan badge (API ringan) | `utils.py` |
| `main` | layout, login, beranda (Varanda), `healthz`, `robots.txt` | `views.py`, `templates/` |

Hak akses **hanya** didefinisikan di `config/roles.py` dan dipakai lewat `@allowed_users(allowed_roles=roles.X)`. Cakupan data (siapa melihat siapa) **hanya** lewat `membro_scope()` di `config/user_utils.py`. Jangan menulis filter wilayah di tempat lain.

## 2. Gaya kode (supaya mudah dibaca)

- View berbentuk fungsi: `@login_required`, `@allowed_users(allowed_roles=[...])`, `group = c_user_group(request.user)`, lalu `context = {...}` dan `render(...)`.
- Satu view per aksi, dikelompokkan per berkas di `views/` (`membro_v.py`, `aprovasaun_v.py`, ...). Nama URL: `app-aksi` (`membro-list`, `aprovasaun-aprova`).
- Logika yang dipakai dua view atau lebih dipindah ke `utils.py` (contoh: `membro_listing()` dipakai daftar **dan** ekspor agar selalu sama).
- Model: `verbose_name` berbahasa Tetun, `Meta.indexes` dan `Meta.constraints` diberi nama eksplisit, pilihan (choices) selalu didefinisikan sekali di `membro/models.py`.
- Indentasi tab, komentar berbahasa Indonesia yang menjelaskan *mengapa*, bukan *apa*.
- Teks tampilan: Tetun. Teks sistem (log, dokumentasi): Indonesia.

## 3. Model dan indeks

Indeks mengikuti query nyata (lihat `membro/models.py`):

| Indeks | Dipakai oleh |
|---|---|
| `hashed` (unik) | setiap URL detail/edit (`get_object_or_404(hashed=...)`) |
| `nu_eleitoral` (unik) | pencegahan duplikat, pencarian awalan |
| `(year, aprovasaun)`, `(village, aprovasaun)`, `(aldeia, aprovasaun)`, `(organizasaun, aprovasaun)` | daftar, Painel, Tabular, notifikasi |
| `(nome, date_of_birth)` | deteksi dobel, urutan nama |
| `date_of_birth`, `telefone` | filter umur, deteksi nomor sama |
| `Alokasaun (ativu, nivel, pozisaun)` | Struktura |
| `Historia (-datetime)`, `(aksaun, -datetime)` | daftar riwayat |

`CheckConstraint` menjaga nilai pilihan di level database (jenis kelamin, status, aprovasaun, nivel, pozisaun). Menambah pilihan baru berarti: ubah daftar di `models.py`, buat migrasi, dan perbarui constraint.

Menambah indeks: tambahkan ke `Meta.indexes`, `python manage.py makemigrations`, uji di salinan data, lalu `bash update.sh` di server.

## 4. Tugas rutin

| Kapan | Apa |
|---|---|
| Harian | `python manage.py backup_data` (PythonAnywhere: tab **Tasks**, jadwal harian). Berisi database dan folder `private/`, 14 salinan terakhir. Unduh salinan ke tempat lain secara berkala. |
| Bulanan | Uji **pemulihan**: unzip cadangan di folder kosong, jalankan `python manage.py check` dengan database itu. Cadangan yang tidak pernah dipulihkan belum tentu bisa dipakai. |
| Tiap pembaruan kode | `bash update.sh` (git pull, pip, **migrate**, collectstatic, check) lalu Reload. |
| Tahunan | Ganti tinan ativu (Data Master), tinjau daftar user (nonaktifkan yang tidak dipakai), perbarui dependensi (bagian 7). |

Pemantauan: `GET /healthz/` mengembalikan `{"status":"ok"}` (200) atau 503 jika database bermasalah; cocok untuk UptimeRobot atau sejenisnya. Log aplikasi: `logs/app.log` (berputar 5 MB x 5) dan error log server.

## 5. Pemulihan dari cadangan (SQLite)

```bash
cd ~/pdpada
mkdir -p /tmp/pulih && unzip backups/pdpada-AAAAMMDD-HHMMSS.zip -d /tmp/pulih
cp db.sqlite3 db.sqlite3.sebelum-pulih            # simpan keadaan sekarang
cp /tmp/pulih/db.sqlite3 db.sqlite3
rm -rf private && cp -r /tmp/pulih/private private  # jika ada
python manage.py check && python manage.py migrate
```

Lalu Reload. `DJANGO_SECRET_KEY` harus sama dengan saat data dibuat (hash di URL dihitung darinya).

## 6. Keamanan yang sudah ada (jangan dilemahkan)

- `hashed` di URL memakai HMAC-SHA256 dengan `SECRET_KEY`; jangan diganti setelah ada data.
- Foto dan PDF eleitoral: isi diperiksa, nama file acak, disimpan di `private/` tanpa URL publik, dibuka hanya lewat `membro-file` yang memeriksa wilayah. Pembukaan PDF dicatat di Historia.
- Ekspor CSV hanya untuk peran Postu, sel dinetralkan dari formula Excel, dan setiap ekspor dicatat.
- Login dibatasi 5 percobaan gagal per (alamat, username) selama 15 menit (cache memori per proses: cukup untuk satu server kecil; gunakan cache bersama bila skala bertambah).
- Cookie sesi HttpOnly, sesi 12 jam, `X-Frame-Options: DENY`, `noindex` di semua halaman.

## 7. Pembaruan dependensi dan versi

- Django **5.2 adalah rilis LTS**; periksa tanggal akhir dukungan di https://www.djangoproject.com/download/ dan rencanakan pindah ke LTS berikutnya **sebelum** tanggal itu. Pindah satu LTS pada satu waktu.
- Prosedur: salin data produksi ke lingkungan uji, naikkan versi di `requirements.txt`, jalankan `python manage.py test` (seluruh tes harus lulus), baca catatan rilis tentang deprecation, `python -W error::DeprecationWarning manage.py check`, baru terapkan.
- Python: pakai versi yang masih didukung (cek https://devguide.python.org/versions/).
- Jangan menghapus migrasi lama. Migrasi adalah sejarah skema.

## 8. Batas skala dan langkah berikutnya

- Daftar membru memakai DataTables di sisi browser: nyaman sampai sekitar 5.000 baris per wilayah. Di atas itu, pindahkan ke pemrosesan sisi server (endpoint DRF dengan paginasi) memakai `membro_listing()` yang sudah ada.
- SQLite cukup untuk satu Postu. Untuk banyak pengguna serentak atau banyak Postu, pindah ke MySQL/PostgreSQL: set `DB_ENGINE=mysql` di `.env`, `dumpdata`/`loaddata` atau alat migrasi, uji dengan `python manage.py test`. `backup_data` hanya untuk SQLite; untuk MySQL gunakan `mysqldump` terjadwal.
- Kartu anggota, notifikasi email/SMS, dan impor massal CSV belum ada; semuanya bisa ditambahkan tanpa mengubah struktur yang ada.

## 9. Menambah hal baru (resep singkat)

- **Peran baru**: tambah konstanta dan label di `config/roles.py`, masukkan ke daftar akses yang sesuai (`INPUT_ROLES`, ...), atur cakupan di `config/user_utils.py` bila perlu, buat grup lewat `seed_inisial`, tambah tes di `membro/tests.py`.
- **Organisasi baru**: Admin menambah di Data Master > Organizasaun; tidak perlu kode.
- **Field baru di Membro**: tambah di model, form (`MembroForm.Meta.fields` dan layout), template detail, `SNAPSHOT_FIELDS` (agar tercatat di riwayat), migrasi, tes.
- **Laporan baru**: fungsi di `report/views/`, template di `report/templates/`, URL, entri menu di `config/context_processors.py`, tes cakupan wilayah.

## 10. Daftar periksa sebelum rilis

1. `python manage.py test` lulus semua.
2. `python manage.py makemigrations --check --dry-run` tidak menemukan perubahan.
3. `DJANGO_DEBUG=False python manage.py check --deploy` hanya menyisakan peringatan HTTPS yang diatur di panel hosting.
4. Cadangan terbaru ada (`backup_data`).
5. Di server: `bash update.sh`, Reload, cek `/healthz/`.
