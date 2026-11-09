from django.db import models
from config.utils import hash_id


class HashedModel(models.Model):
	"""Model dasar dengan kolom hashed (HMAC-SHA256) yang terisi otomatis setelah id ada."""
	# hashed dipakai untuk mencari data di setiap URL (get_object_or_404(hashed=...)): unik dan terindeks
	hashed = models.CharField(max_length=64, null=True, blank=True, editable=False, unique=True)

	class Meta:
		abstract = True

	def save(self, *args, **kwargs):
		super().save(*args, **kwargs)
		if not self.hashed:
			self.hashed = hash_id(f'{self._meta.label}:{self.pk}')
			super().save(update_fields=['hashed'])
