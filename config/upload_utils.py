import os
from uuid import uuid4
from django.core.exceptions import ValidationError

MAX_IMAGE_MB = 2
IMAGE_EXTS = ('jpg', 'jpeg', 'png')


def upload_foto(instance, filename):
	ext = filename.rsplit('.', 1)[-1].lower()
	if ext not in IMAGE_EXTS:
		ext = 'jpg'
	return os.path.join('membro_foto', '{}.{}'.format(uuid4().hex, ext))


def validate_image_size(image):
	if image.size > MAX_IMAGE_MB * 1024 * 1024:
		raise ValidationError(f'Fotu boot liu {MAX_IMAGE_MB} MB.')
