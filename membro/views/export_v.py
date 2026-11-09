import csv
import logging
from django.contrib.auth.decorators import login_required
from django.http import StreamingHttpResponse
from django.utils import timezone
from config import roles
from config.decorators import allowed_users
from membro.utils import membro_listing, log_historia, CSV_HEADER, csv_row


logger = logging.getLogger('pdpada')


class Echo:
	"""Pseudo-buffer: csv.writer menulis ke sini dan hasilnya langsung di-stream (hemat memori)."""
	def write(self, value):
		return value


@login_required
@allowed_users(allowed_roles=roles.EXPORT_ROLES)
def MembroExport(request):
	"""Ekspor CSV penuh sesuai filter dan wilayah user (bukan hanya halaman yang tampil).
	Setiap ekspor dicatat di Historia karena memuat data pribadi."""
	objects, _ = membro_listing(request.user, request.GET)
	total = objects.count()
	filtru = request.GET.urlencode() or '(laiha filtru)'
	log_historia(request.user, None, 'Ekspor', f'{total} membru · filtru: {filtru}', nome='Ekspor CSV')
	logger.info('ekspor CSV oleh %s: %s membru, filtru=%s', request.user.get_username(), total, filtru)

	def rows():
		writer = csv.writer(Echo())
		yield '﻿'  # BOM agar Excel membaca UTF-8 dengan benar
		yield writer.writerow(CSV_HEADER)
		for m in objects.iterator(chunk_size=500):
			yield writer.writerow(csv_row(m))

	response = StreamingHttpResponse(rows(), content_type='text/csv; charset=utf-8')
	stamp = timezone.localtime().strftime('%Y%m%d-%H%M')
	response['Content-Disposition'] = f'attachment; filename="membru-{stamp}.csv"'
	response['Cache-Control'] = 'private, no-store'
	response['X-Content-Type-Options'] = 'nosniff'
	return response
