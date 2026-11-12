import datetime
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.db import models
from config.models import HashedModel
from config.file_utils import validate_image_content, validate_pdf_content, validate_pdf_size
from config.storage import private_storage
from config.upload_utils import upload_foto, upload_eleitoral, validate_image_size
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
	telefone = models.CharField(max_length=20, null=True, blank=True, verbose_name="Nu. Telemovel",
			validators=[RegexValidator(r'^[0-9+\- ]{7,20}$', 'Nu. telemovel la loos.')])
	image = models.ImageField(upload_to=upload_foto, storage=private_storage, null=True, blank=True, verbose_name="Fotu",
			validators=[validate_image_size, validate_image_content])
	file_eleitoral = models.FileField(upload_to=upload_eleitoral, storage=private_storage, null=True, blank=True,
			verbose_name="Kartaun Eleitoral (PDF)", validators=[validate_pdf_size, validate_pdf_content])
	village = models.ForeignKey(Village, on_delete=models.PROTECT, verbose_name="Suku")
	aldeia = models.ForeignKey(Aldeia, on_delete=models.PROTECT, verbose_name="Aldeia")
	address = models.CharField(max_length=100, null=True, blank=True, verbose_name="Hela Fatin")
	organizasaun = models.ForeignKey(Organizasaun, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Organizasaun")
	data_hakbit = models.DateField(null=True, blank=True, verbose_name="Data Hakbit (Tama PD)")
	status = models.CharField(choices=STATUS, max_length=10, default='Ativu', verbose_name="Status")
	aprovasaun = models.CharField(choices=APROVASAUN, max_length=10, default='Pendente', verbose_name="Aprovasaun")
	is_colocado = models.BooleanField(default=False, db_index=True, verbose_name="Iha Pozisaun")  # TRUE = iha pozisaun ativu; la hatudu iha form aloka
	razaun_rejeita = models.TextField(null=True, blank=True, verbose_name="Razaun Rejeita")
	aprovadu_husi = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
	data_aprovasaun = models.DateTimeField(null=True, blank=True)
	year = models.ForeignKey(Year, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Tinan")
	datetime = models.DateTimeField(null=True)
	user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+')

	class Meta:
		ordering = ['nome']
		# Indeks mengikuti query nyata: daftar/dashboard per wilayah + status, pencarian nama,
		# deteksi dobel (nama + tanggal lahir). nu_eleitoral dan hashed sudah unik (terindeks).
		indexes = [
			models.Index(fields=['nome', 'date_of_birth'], name='membro_nome_dob_idx'),
			models.Index(fields=['year', 'aprovasaun'], name='membro_year_aprov_idx'),
			models.Index(fields=['village', 'aprovasaun'], name='membro_vil_aprov_idx'),
			models.Index(fields=['aldeia', 'aprovasaun'], name='membro_ald_aprov_idx'),
			models.Index(fields=['organizasaun', 'aprovasaun'], name='membro_org_aprov_idx'),
			models.Index(fields=['date_of_birth'], name='membro_dob_idx'),
			models.Index(fields=['telefone'], name='membro_telefone_idx'),
		]
		# Integritas di level database (bukan hanya form): nilai pilihan harus valid
		constraints = [
			models.CheckConstraint(condition=models.Q(sex__in=[c[0] for c in SEXU]), name='membro_sex_valid'),
			models.CheckConstraint(condition=models.Q(aprovasaun__in=[c[0] for c in APROVASAUN]), name='membro_aprovasaun_valid'),
			models.CheckConstraint(condition=models.Q(status__in=[c[0] for c in STATUS]), name='membro_status_valid'),
		]

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
		indexes = [models.Index(fields=['ativu', 'nivel', 'pozisaun'], name='aloka_ativu_niv_poz_idx')]
		constraints = [
			models.CheckConstraint(condition=models.Q(nivel__in=[c[0] for c in NIVEL]), name='aloka_nivel_valid'),
			models.CheckConstraint(condition=models.Q(pozisaun__in=[c[0] for c in POZISAUN]), name='aloka_pozisaun_valid'),
			models.CheckConstraint(condition=models.Q(ativu__in=['Sim', 'Lae']), name='aloka_ativu_valid'),
		]

	def save(self, *args, **kwargs):
		old = Alokasaun.objects.filter(pk=self.pk).values_list('membro_id', flat=True).first() if self.pk else None
		super().save(*args, **kwargs)
		sync_colocado(self.membro_id)
		if old and old != self.membro_id:  # alokasaun dipindah ke membru lain
			sync_colocado(old)

	def delete(self, *args, **kwargs):
		membro_id = self.membro_id
		result = super().delete(*args, **kwargs)
		sync_colocado(membro_id)
		return result

	def unit(self):
		return self.aldeia or self.village or self.organizasaun

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
		indexes = [
			models.Index(fields=['-datetime'], name='historia_datetime_idx'),
			models.Index(fields=['aksaun', '-datetime'], name='historia_aksaun_idx'),
		]

	def nama_pendek(self):
		"""Naran membru tanpa Nu. Eleitoral, untuk daftar yang ringkas."""
		return self.membro_nome.split(' (')[0]

	def __str__(self):
		template = '{0.datetime:%Y-%m-%d %H:%M} {0.aksaun} {0.membro_nome}'
		return template.format(self)


def sync_colocado(membro_id):
	"""is_colocado = TRUE selama membru punya pozisaun ativu; FALSE setelah termina atau dihapus (data lama tetap tersimpan)."""
	if membro_id:
		Membro.objects.filter(pk=membro_id).update(is_colocado=Alokasaun.objects.filter(membro_id=membro_id, ativu='Sim').exists())
