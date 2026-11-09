"""Pemeriksaan ISI file upload (bukan hanya ekstensi): foto dan PDF kartu eleitoral."""
import io
import re
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_PIXELS = 25_000_000      # 25 megapiksel
MAX_SIDE = 1600              # sisi terpanjang foto setelah dibersihkan
ALLOWED_IMAGE_FORMATS = {'JPEG', 'PNG'}
MAX_PDF_MB = 5
MAX_PDF_PAGES = 20

# nama PDF yang menandakan konten aktif / lampiran / aksi berbahaya
PDF_DANGEROUS = re.compile(
	rb'/(JavaScript|JS|Launch|EmbeddedFile|EmbeddedFiles|OpenAction|AA|RichMedia|XFA|GoToR|GoToE|SubmitForm|ImportData|Rendition|Sound|Movie)(?![A-Za-z0-9])')
PDF_BAD_ACTIONS = {'/JavaScript', '/Launch', '/GoToR', '/GoToE', '/SubmitForm', '/ImportData', '/Rendition', '/Sound', '/Movie'}


def validate_image_content(f):
	"""Foto harus benar-benar JPEG/PNG yang bisa didekode; isi diperiksa dengan Pillow."""
	try:
		f.seek(0)
		with Image.open(f) as img:
			fmt, (w, h) = img.format, img.size
			if fmt not in ALLOWED_IMAGE_FORMATS:
				raise ValidationError("Fotu tenke JPEG ka PNG ne'ebé loos.")
			if w * h > MAX_PIXELS:
				raise ValidationError('Fotu boot liu (maksimu 25 megapixel).')
			img.verify()
		f.seek(0)
		with Image.open(f) as img:
			img.load()  # dekode penuh: file terpotong/rusak ditolak
	except ValidationError:
		raise
	except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError):
		raise ValidationError("Fotu la válidu: ficheiru ne'e la'ós imajen JPEG ka PNG ne'ebé loos.")
	finally:
		try:
			f.seek(0)
		except Exception:
			pass


def sanitize_image(upload):
	"""Dekode lalu encode ulang sebagai JPEG baru: buang EXIF/metadata dan data tambahan
	yang ditempel di file (polyglot), putar sesuai orientasi, kecilkan ukuran."""
	upload.seek(0)
	with Image.open(upload) as img:
		img = ImageOps.exif_transpose(img)
		if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
			rgba = img.convert('RGBA')
			bg = Image.new('RGB', rgba.size, (255, 255, 255))
			bg.paste(rgba, mask=rgba.split()[-1])
			img = bg
		else:
			img = img.convert('RGB')
		img.thumbnail((MAX_SIDE, MAX_SIDE))
		buf = io.BytesIO()
		img.save(buf, 'JPEG', quality=85, optimize=True)  # tanpa exif=: metadata tidak ikut
	return ContentFile(buf.getvalue(), name='foto.jpg')


def validate_pdf_size(f):
	if f.size > MAX_PDF_MB * 1024 * 1024:
		raise ValidationError(f'PDF boot liu (maksimu {MAX_PDF_MB} MB).')


def validate_pdf_content(f):
	"""PDF harus benar-benar PDF (header, penutup, bisa di-parse), tidak terenkripsi, jumlah
	halaman wajar, dan tidak memuat JavaScript, lampiran, atau aksi peluncuran."""
	from pypdf import PdfReader
	try:
		f.seek(0)
		data = f.read()
		f.seek(0)
	except Exception:
		raise ValidationError("PDF la bele lee.")
	if not data.startswith(b'%PDF-'):
		raise ValidationError("Ficheiru la'ós PDF ne'ebé válidu.")
	if b'%%EOF' not in data[-2048:]:
		raise ValidationError('PDF la kompletu ka korrompidu.')
	if PDF_DANGEROUS.search(data):
		raise ValidationError("PDF iha kódigu ativu (JavaScript/aksaun/anexu) no la bele simu.")
	try:
		reader = PdfReader(io.BytesIO(data))
		if reader.is_encrypted:
			raise ValidationError('PDF proteje ho password la bele simu.')
		n = len(reader.pages)
		if n < 1:
			raise ValidationError('PDF laiha pájina.')
		if n > MAX_PDF_PAGES:
			raise ValidationError(f'PDF iha pájina barak liu (maksimu {MAX_PDF_PAGES}).')
		root = reader.trailer['/Root']
		if '/OpenAction' in root or '/AA' in root:
			raise ValidationError("PDF iha aksaun automátiku no la bele simu.")
		names = root.get('/Names')
		if names is not None:
			names = names.get_object()
			if '/JavaScript' in names or '/EmbeddedFiles' in names:
				raise ValidationError("PDF iha JavaScript ka anexu no la bele simu.")
		acro = root.get('/AcroForm')
		if acro is not None and '/XFA' in acro.get_object():
			raise ValidationError("PDF ho formuláriu XFA la bele simu.")
		for page in reader.pages:
			if '/AA' in page:
				raise ValidationError("PDF iha aksaun automátiku no la bele simu.")
			annots = page.get('/Annots')
			for a in (annots.get_object() if annots is not None else []):
				action = a.get_object().get('/A')
				if action is not None and action.get_object().get('/S') in PDF_BAD_ACTIONS:
					raise ValidationError("PDF iha ligasaun/aksaun perigu no la bele simu.")
	except ValidationError:
		raise
	except Exception:
		raise ValidationError("PDF la válidu ka korrompidu.")
