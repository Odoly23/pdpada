#!/usr/bin/env bash
# Pembaruan di server (PythonAnywhere): bash update.sh
# Menjalankan semua langkah yang sering terlupa: kode, paket, MIGRASI, static, pengecekan.
# Error "no such column ..." berarti migrate belum dijalankan.
set -euo pipefail
cd "$(dirname "$0")"
git pull --ff-only origin "$(git rev-parse --abbrev-ref HEAD)"
pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py check
echo
echo "Selesai. Klik tombol Reload di tab Web PythonAnywhere."
