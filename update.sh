#!/usr/bin/env bash
# Pembaruan di server (PythonAnywhere): bash update.sh
# Menjalankan semua langkah yang sering terlupa: kode, paket, MIGRASI, static, pengecekan.
# Error "no such column ..." berarti migrate belum dijalankan.
#
# Jika git menolak ("Not possible to fast-forward"), riwayat git di server berbeda dari GitHub
# (biasanya karena `git pull` biasa membuat commit gabungan lokal). Server tidak boleh punya
# perubahan sendiri, jadi samakan dengan GitHub:  bash update.sh --reset
# (.env, database, folder private/ dan backups/ tidak tersentuh karena tidak dilacak git).
set -euo pipefail
cd "$(dirname "$0")"

RESET=0
[ "${1:-}" = "--reset" ] && RESET=1
BRANCH="$(git rev-parse --abbrev-ref HEAD)"

git fetch origin
if [ "$RESET" = "1" ]; then
	if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
		echo "Dibatalkan: ada perubahan lokal pada file yang dilacak git. Periksa dengan: git status" >&2
		exit 1
	fi
	git reset --hard "origin/$BRANCH"
elif ! git merge --ff-only "origin/$BRANCH"; then
	echo >&2
	echo "Riwayat git di server berbeda dari GitHub (branch: $BRANCH)." >&2
	echo "Samakan dengan GitHub:  bash update.sh --reset" >&2
	exit 1
fi

# UPDATE_SKIP_APP=1 hanya dipakai untuk menguji bagian git
if [ "${UPDATE_SKIP_APP:-0}" != "1" ]; then
	pip install -r requirements.txt
	python manage.py migrate --noinput
	python manage.py collectstatic --noinput
	python manage.py check
fi

echo
echo "Selesai. Klik tombol Reload di tab Web PythonAnywhere."
