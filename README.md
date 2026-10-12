# APORTIL e-Ticketing (Bilheteira)

Sistem tiket kapal APORTIL Timor-Leste: Dili–Ataúro, Dili–Oecusse. Django, mobile-first, 4 bahasa (Tetun default, PT, EN, ID).

## Jalankan lokal
```
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate && python manage.py createcachetable
python manage.py setup_roles          # grup: Admin APORTIL, Resepsionista, Inspector, Operator
python manage.py createsuperuser
python manage.py runserver
```

## Terjemahan
Teks sumber = Tetun. Tambah terjemahan di `scripts/translations.py`, lalu `python scripts/build_locale.py` (tanpa gettext).

## Tugas terjadwal (cron)
- `python manage.py purge_documents` — hapus foto dokumen > 30 hari (harian).

## Status
Fase 1 selesai: fondasi, model data, login aman (5x gagal → kunci, sesi 30 menit), audit log, halaman publik, grup/izin.
Berikutnya: penjualan tiket di loket + cetak thermal 80mm, scan QR (PWA offline), jadwal/kuota/pengumuman, refund medis, laporan email harian/bulanan/tahunan, deploy.
