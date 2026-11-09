import os
from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateStorage(FileSystemStorage):
	"""Penyimpanan di luar MEDIA_ROOT: file tidak punya URL publik dan hanya
	bisa dibuka lewat view yang memeriksa hak akses (lihat membro-file)."""

	@property
	def base_location(self):
		return settings.PRIVATE_ROOT

	@property
	def location(self):
		return os.path.abspath(self.base_location)

	@property
	def base_url(self):
		return None  # .url -> ValueError: sengaja tidak bisa diakses publik


_private = PrivateStorage()


def private_storage():
	return _private
