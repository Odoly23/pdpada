from django.contrib.auth.models import User
from django.db import models
from custom.models import Village, Aldeia, Organizasaun


class UserScope(models.Model):
	"""Wilayah atau organisasi yang boleh dilihat user (selain peran tingkat Postu)."""
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='scope')
	village = models.ForeignKey(Village, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Suku")
	aldeia = models.ForeignKey(Aldeia, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Aldeia")
	organizasaun = models.ForeignKey(Organizasaun, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Organizasaun")

	def __str__(self):
		template = '{0.user}'
		return template.format(self)
