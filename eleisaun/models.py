from django.contrib.auth.models import User
from django.db import models
from config.file_utils import validate_image_content
from config.storage import private_storage
from config.upload_utils import upload_resultado_foto, validate_image_size
from custom.models import Village, Aldeia


class Eleisaun(models.Model):
	"""Satu pemilu (misalnya tiap 5 tahun). Hanya satu yang boleh aktif (dashboard live) pada satu waktu."""
	naran = models.CharField(max_length=120, verbose_name="Naran Eleisaun")
	tinan = models.PositiveSmallIntegerField(verbose_name="Tinan")
	ativu = models.BooleanField(default=False, db_index=True, verbose_name="Live Dashboard Ativu")
	criadu = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-tinan', '-id']

	def save(self, *args, **kwargs):
		super().save(*args, **kwargs)
		if self.ativu:  # satu pemilu live saja
			Eleisaun.objects.exclude(pk=self.pk).filter(ativu=True).update(ativu=False)

	def __str__(self):
		return f'{self.naran} ({self.tinan})'


class TempatVoting(models.Model):
	naran = models.CharField(max_length=120, verbose_name="Naran Tempat Votasaun")
	village = models.ForeignKey(Village, on_delete=models.PROTECT, verbose_name="Suku")
	aldeia = models.ForeignKey(Aldeia, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Aldeia")
	ativu = models.BooleanField(default=True, verbose_name="Ativu")

	class Meta:
		ordering = ['village__name', 'naran']
		constraints = [models.UniqueConstraint(fields=['naran', 'village'], name='tempat_naran_suku_unik')]

	def __str__(self):
		return self.naran


class FiskaisTempat(models.Model):
	"""Fiskais (akun dengan peran Fiskais Partidu) yang bertugas di satu tempat votasaun."""
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='fiskais_tempat', verbose_name="Fiskais")
	tempat = models.ForeignKey(TempatVoting, on_delete=models.PROTECT, related_name='fiskais', verbose_name="Tempat")

	class Meta:
		ordering = ['tempat__naran', 'user__username']

	def __str__(self):
		return f'{self.user.get_username()} @ {self.tempat}'


class Resultado(models.Model):
	"""Hasil votu partidu di satu tempat untuk satu eleisaun. Terkunci setelah disubmit sampai Admin membuka lagi."""
	eleisaun = models.ForeignKey(Eleisaun, on_delete=models.PROTECT, related_name='resultados', verbose_name="Eleisaun")
	tempat = models.ForeignKey(TempatVoting, on_delete=models.PROTECT, related_name='resultados', verbose_name="Tempat")
	votos_partidu = models.PositiveIntegerField(verbose_name="Total Votu PD")
	foto = models.ImageField(upload_to=upload_resultado_foto, storage=private_storage, verbose_name="Foto Rezultadu", validators=[validate_image_size, validate_image_content])
	submetidu = models.BooleanField(default=False, db_index=True, verbose_name="Submetidu (terkunci)")
	submetidu_em = models.DateTimeField(null=True, blank=True)
	submetidu_husi = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
	atualizadu = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['tempat__naran']
		constraints = [models.UniqueConstraint(fields=['eleisaun', 'tempat'], name='resultado_unik_eleisaun_tempat')]

	def __str__(self):
		return f'{self.tempat} · {self.votos_partidu}'
