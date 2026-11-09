import os
from uuid import uuid4
from django.core.exceptions import ValidationError
from config.utils import hash_id

MAX_IMAGE_MB = 2
IMAGE_EXTS = ('jpg', 'jpeg', 'png')


def _secure_name(folder, ext):
	"""Nama file baru: HMAC-SHA256 dari token acak. Nama asli dari pengguna tidak dipakai."""
	return os.path.join(folder, '{}.{}'.format(hash_id(uuid4().hex + uuid4().hex), ext))


def upload_foto(instance, filename):
	return _secure_name('foto', 'jpg')  # foto selalu dikonversi ke JPEG oleh sanitize_image


def upload_eleitoral(instance, filename):
	return _secure_name('eleitoral', 'pdf')


def validate_image_size(image):
	if image.size > MAX_IMAGE_MB * 1024 * 1024:
		raise ValidationError(f'Fotu boot liu {MAX_IMAGE_MB} MB.')
