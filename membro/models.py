import datetime
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.db import models
from config.models import HashedModel
from config.upload_utils import upload_foto, validate_image_size
from custom.models import Village, Aldeia, Organizasaun, Year

SEXU = [('Mane', 'Mane'), ('Feto', 'Feto')]
MARITAL = [('Solteiro/a', 'Solteiro/a'), ('Casado/a', 'Casado/a'), ('Divorciado/a', 'Divorciado/a'), ('Viuvo/a', 'Viuvo/a')]
STATUS = [('Ativu', 'Ativu'), ('Inativu', 'Inativu'), ('Falesidu', 'Falesidu')]
APROVASAUN = [('Pendente', 'Pendente'), ('Aprovadu', 'Aprovadu'), ('Rejeitadu', 'Rejeitadu')]

NIVEL = [('Postu', 'Postu'), ('Suku', 'Suku'), ('Aldeia', 'Aldeia'), ('Organizasaun', 'Organizasaun')]
POZISAUN = [('Presidente', 'Presidente'), ('Coordenador', 'Coordenador'), ('Sekretariu', 'Sekretariu')]
POZISAUN_POR_NIVEL = {
	'Postu': ['Presidente', 'Coordenador', 'Sekretariu'],
	'Suku': ['Coordenador', 'Sekretariu'],
	'Aldeia': ['Coordenador', 'Sekretariu'],
	'Organizasaun': ['Coordenador', 'Sekretariu'],
}


class Membro(HashedModel):
	nome = models.CharField(max_length=100, verbose_name="Naran")
	sex = models.CharField(choices=SEXU, max_length=6, verbose_name="Sexu")
	place_of_birth = models.CharField(max_length=100, blank=True, null=True, verbose_name="Fatin Moris")
	date_of_birth = models.DateField(verbose_name="Data Moris")
	marital = models.CharField(choices=MARITAL, max_length=15, null=True, blank=True, verbose_name="Estado Civil")
	nu_eleitoral = models.CharField(max_length=30, unique=True, verbose_name="Nu. Eleitoral",
			validators=[RegexValidator(r'^[A-Za-z0-9\-/]{4,30}$', 'Deit letra, numeru, "-" no "/" (4 to 30 karakter).')])
	nu_bi = models.CharField(max_length=30, null=True, blank=True, verbose_name="Nu. BI")
	telefone = models.CharField(max_length=20, null=True, blank=True, verbose_name="Nu. Telemovel",
			validators=[RegexValidator(r'^[0-9+\- ]{7,20}$', 'Nu. telemovel la loos.')])
	image = models.ImageField(upload_to=upload_foto, null=True, blank=True, verbose_name="Fotu",
			validators=[validate_image_size])
	village = models.ForeignKey(Village, on_delete=models.PROTECT, verbose_name="Suku")
	aldeia = models.ForeignKey(Aldeia, on_delete=models.PROTECT, verbose_name="Aldeia")
	address = models.CharField(max_length=100, null=True, blank=True, verbose_name="Hela Fatin")
	organizasaun = models.ForeignKey(Organizasaun, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Organizasaun")
	data_hakbit = models.DateField(null=True, blank=True, verbose_name="Data Hakbit (Tama PD)")
	status = models.CharField(choices=STATUS, max_length=10, default='Ativu', verbose_name="Status")
	aprovasaun = models.CharField(choices=APROVASAUN, max_length=10, default='Pendente', verbose_name="Aprovasaun")
	razaun_rejeita = models.TextField(null=True, blank=True, verbose_name="Razaun Rejeita")
	aprovadu_husi = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
	data_aprovasaun = models.DateTimeField(null=True, blank=True)
	year = models.ForeignKey(Year, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Tinan")
	datetime = models.DateTimeField(null=True)
	user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+')

	class Meta:
		ordering = ['nome']

	def __str__(self):
		template = '{0.nome} ({0.nu_eleitoral})'
		return template.format(self)

	def age(self):
		if not self.date_of_birth:
			return None
		return int((datetime.date.today() - self.date_of_birth).days // 365.2425)


class Alokasaun(models.Model):
	"""Pozisaun/kargu ne'ebé Presidente Postu aloka ba membru (modelu hanesan Kolokasaun)."""
	membro = models.ForeignKey(Membro, on_delete=models.CASCADE, related_name='alokasaun', verbose_name="Membru")
	nivel = models.CharField(choices=NIVEL, max_length=15, verbose_name="Nivel")
	pozisaun = models.CharField(choices=POZISAUN, max_length=15, verbose_name="Pozisaun")
	village = models.ForeignKey(Village, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Suku")
	aldeia = models.ForeignKey(Aldeia, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Aldeia")
	organizasaun = models.ForeignKey(Organizasaun, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Organizasaun")
	data_hahu = models.DateField(verbose_name="Data Hahu")
	data_termina = models.DateField(null=True, blank=True, verbose_name="Data Termina")
	ativu = models.CharField(choices=[('Sim', 'Sim'), ('Lae', 'Lae')], max_length=3, default='Sim', verbose_name="Ativu")
	datetime = models.DateTimeField(null=True)
	user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+')

	class Meta:
		ordering = ['-ativu', 'nivel', 'pozisaun']

	def unit(self):
		return self.village or self.aldeia or self.organizasaun

	def __str__(self):
		template = '{0.membro} - {0.pozisaun} {0.nivel}'
		return template.format(self)


class Historia(models.Model):
	"""Log mudansa data (kria, edita, aprova, rejeita, hamoos, aloka)."""
	membro = models.ForeignKey(Membro, on_delete=models.SET_NULL, null=True, blank=True, related_name='historia')
	membro_nome = models.CharField(max_length=150, blank=True)
	aksaun = models.CharField(max_length=30)
	detalhe = models.TextField(blank=True)
	datetime = models.DateTimeField(auto_now_add=True)
	user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+')

	class Meta:
		ordering = ['-datetime', '-id']

	def __str__(self):
		template = '{0.datetime:%Y-%m-%d %H:%M} {0.aksaun} {0.membro_nome}'
		return template.format(self)
