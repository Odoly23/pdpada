from django.db import models
from config.models import HashedModel


class Municipality(models.Model):
	code = models.CharField(max_length=5, null=True, blank=True)
	name = models.CharField(max_length=100, verbose_name="Naran")

	def __str__(self):
		template = '{0.name}'
		return template.format(self)


class AdministrativePost(models.Model):
	municipality = models.ForeignKey(Municipality, on_delete=models.CASCADE, null=True)
	name = models.CharField(max_length=100, verbose_name="Naran")

	def __str__(self):
		template = '{0.name}'
		return template.format(self)


class Village(models.Model):
	administrativepost = models.ForeignKey(AdministrativePost, on_delete=models.CASCADE, null=True, verbose_name="Postu")
	name = models.CharField(max_length=100, verbose_name="Naran Suku")

	class Meta:
		ordering = ['name']

	def __str__(self):
		template = '{0.name}'
		return template.format(self)


class Aldeia(models.Model):
	village = models.ForeignKey(Village, on_delete=models.CASCADE, null=True, verbose_name="Suku")
	name = models.CharField(max_length=100, verbose_name="Naran Aldeia")

	class Meta:
		ordering = ['village__name', 'name']

	def __str__(self):
		template = '{0.name}'
		return template.format(self)


class Organizasaun(HashedModel):
	code = models.CharField(max_length=10, verbose_name="Kódigu")
	name = models.CharField(max_length=100, verbose_name="Naran")
	is_active = models.BooleanField(default=True, verbose_name="Ativu")

	class Meta:
		ordering = ['code']

	def __str__(self):
		template = '{0.code}'
		return template.format(self)


class Year(models.Model):
	year = models.IntegerField(unique=True, verbose_name="Tinan")
	is_active = models.BooleanField(default=False, verbose_name="Ativu")

	class Meta:
		ordering = ['-year']

	def save(self, *args, **kwargs):
		super().save(*args, **kwargs)
		if self.is_active:
			Year.objects.exclude(pk=self.pk).filter(is_active=True).update(is_active=False)

	def __str__(self):
		template = '{0.year}'
		return template.format(self)
