import sqlite3
import tempfile
import zipfile
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone


class Command(BaseCommand):
	help = ('Cadangan data: salinan konsisten database SQLite + folder privat (foto dan PDF eleitoral) dalam satu ZIP '
		'bertanda waktu, dengan rotasi otomatis. Jalankan harian (PythonAnywhere: tab Tasks).')

	def add_arguments(self, parser):
		parser.add_argument('--dir', default=str(Path(settings.BASE_DIR) / 'backups'), help='Folder tujuan (default: <proyek>/backups)')
		parser.add_argument('--keep', type=int, default=14, help='Jumlah cadangan terbaru yang disimpan (default 14)')

	def handle(self, *args, **options):
		engine = settings.DATABASES['default']['ENGINE']
		if 'sqlite' not in engine:
			raise CommandError('Backup otomatis hanya untuk SQLite. Untuk MySQL gunakan mysqldump.')
		if connection.in_atomic_block:
			# backup SQLite menunggu lock tanpa batas bila ada transaksi terbuka di koneksi yang sama
			raise CommandError('Backup tidak boleh dijalankan di dalam transaksi terbuka.')
		if options['keep'] < 1:
			raise CommandError('--keep minimal 1.')
		out_dir = Path(options['dir'])
		out_dir.mkdir(parents=True, exist_ok=True)
		target = out_dir / f"pdpada-{timezone.localtime().strftime('%Y%m%d-%H%M%S')}.zip"

		with tempfile.TemporaryDirectory() as tmp:
			snapshot = Path(tmp) / 'db.sqlite3'
			connection.ensure_connection()
			dest = sqlite3.connect(snapshot)
			try:
				connection.connection.backup(dest)  # API backup SQLite: aman walau database sedang dipakai
			finally:
				dest.close()
			with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
				archive.write(snapshot, 'db.sqlite3')
				private = Path(settings.PRIVATE_ROOT)
				if private.exists():
					for path in sorted(private.rglob('*')):
						if path.is_file():
							archive.write(path, 'private/' + path.relative_to(private).as_posix())
		target.chmod(0o600)  # berisi data pribadi: hanya pemilik

		old = sorted(out_dir.glob('pdpada-*.zip'), reverse=True)[options['keep']:]
		for path in old:
			path.unlink()
		self.stdout.write(self.style.SUCCESS(
			f'Cadangan dibuat: {target} ({target.stat().st_size // 1024} KB). Dihapus (rotasi): {len(old)}.'))
		self.stdout.write('Unduh dan simpan salinan di luar server (tab Files PythonAnywhere atau penyimpanan lain).')
