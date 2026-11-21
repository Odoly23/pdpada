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
KATEGORIA = [('Militante', 'Militante & Simpatizante')]  # kategoria ida deit (Militante no Simpatizante hamutuk)
JENIS_LIST = ['Struktura', 'Militante']  # Struktura = iha pozisaun ativu (is_colocado)
JENIS_LABEL = {'Struktura': 'Struktura Penting', 'Militante': 'Militante & Simpatizante'}
MARITAL = [('Klosan', 'Klosan'), ("Kaben-na'in", "Kaben-na'in"), ('Fahe malu', 'Fahe malu'), ('Faluk', 'Faluk')]
STATUS = [('Ativu', 'Ativu'), ('Inativu', 'Inativu'), ('Falesidu', 'Falesidu')]
APROVASAUN = [('Pendente', 'Pendente'), ('Aprovadu', 'Aprovadu'), ('Rejeitadu', 'Rejeitadu')]

NIVEL = [('Postu', 'Postu'), ('Suku', 'Suku'), ('Aldeia', 'Aldeia'), ('Organizasaun', 'Organizasaun')]


class Pozisaun(models.Model):
	"""Data mestre pozisaun (Presidente, Vice I-III, Coordenador, Sekretariu, ...). Alokasaun.pozisaun rai naran husi tabela ne'e;
	kampu iha_* hatudu iha nivel ida-ne'ebé pozisaun ne'e bele uza."""
	naran = models.CharField(max_length=60, unique=True, verbose_name="Naran Pozisaun")
	urutan = models.PositiveSmallIntegerField(default=10, verbose_name="Urutan")
	iha_postu = models.BooleanField(default=False, verbose_name="Nivel Postu")
	iha_suku = models.BooleanField(default=False, verbose_name="Nivel Suku")
	iha_aldeia = models.BooleanField(default=False, verbose_name="Nivel Aldeia")
	iha_organizasaun = models.BooleanField(default=False, verbose_name="Nivel Organizasaun")
	ativu = models.BooleanField(default=True, verbose_name="Ativu")
	unik = models.BooleanField(default=True, verbose_name="Unik (ema ida deit iha unidade)")  # Membru Seksaun: barak

	class Meta:
		ordering = ['urutan', 'naran']
		verbose_name = 'Pozisaun'
		verbose_name_plural = 'Pozisaun'

	def nivel_list(self):
		return [n for n, on in (('Postu', self.iha_postu), ('Suku', self.iha_suku), ('Aldeia', self.iha_aldeia), ('Organizasaun', self.iha_organizasaun)) if on]

	def __str__(self):
		return self.naran


def pozisaun_por_nivel():
	"""{nivel: [naran pozisaun ativu tuir urutan]} husi tabela Pozisaun."""
	result = {n: [] for n, _ in NIVEL}
	for p in Pozisaun.objects.filter(ativu=True):
		for n in p.nivel_list():
			result[n].append(p.naran)
	return result


class Membro(HashedModel):
	nome = models.CharField(max_length=100, verbose_name="Naran")
	sex = models.CharField(choices=SEXU, max_length=6, verbose_name="Sexu")
	place_of_birth = models.CharField(max_length=100, blank=True, null=True, verbose_name="Fatin Moris")
	date_of_birth = models.DateField(verbose_name="Data Moris")
	marital = models.CharField(choices=MARITAL, max_length=15, null=True, blank=True, verbose_name="Estadu sivíl")
	kategoria = models.CharField(choices=KATEGORIA, max_length=12, default='Militante', db_index=True, verbose_name="Kategoria")
	nu_eleitoral = models.CharField(max_length=30, unique=True, null=True, blank=True, verbose_name="Nu. Eleitoral",
			validators=[RegexValidator(r'^[A-Za-z0-9\-/]{4,30}$', 'Deit letra, numeru, "-" no "/" (4 to 30 karakter).')])
	telefone = models.CharField(max_length=20, null=True, blank=True, verbose_name="Nu. Telemóvel",
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
	status = models.CharField(choices=STATUS, max_length=10, default='Ativu', verbose_name="Situasaun")
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
			models.CheckConstraint(condition=models.Q(kategoria__in=[c[0] for c in KATEGORIA]), name='membro_kategoria_valid'),
		]

	def __str__(self):
		return f'{self.nome} ({self.nu_eleitoral})' if self.nu_eleitoral else self.nome

	def jenis(self):
		"""Struktura (iha pozisaun ativu) ka Militante (Militante & Simpatizante, kategoria ida deit)."""
		return 'Struktura' if self.is_colocado else 'Militante'

	def jenis_label(self):
		return JENIS_LABEL[self.jenis()]

	def age(self):
		if not self.date_of_birth:
			return None
		return int((datetime.date.today() - self.date_of_birth).days // 365.2425)


class Alokasaun(models.Model):
	"""Pozisaun/kargu ne'ebé Presidente Postu aloka ba membru (modelu hanesan Kolokasaun)."""
	membro = models.ForeignKey(Membro, on_delete=models.CASCADE, related_name='alokasaun', verbose_name="Membru")
	nivel = models.CharField(choices=NIVEL, max_length=15, verbose_name="Nivel")
	pozisaun = models.CharField(max_length=60, verbose_name="Pozisaun")  # naran husi tabela Pozisaun
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
			models.CheckConstraint(condition=models.Q(ativu__in=['Sim', 'Lae']), name='aloka_ativu_valid'),
		]

	def save(self, *args, **kwargs):
		old = Alokasaun.objects.filter(pk=self.pk).values_list('membro_id', flat=True).first() if self.pk else None
		super().save(*args, **kwargs)
		sync_colocado(self.membro_id)
		if self.organizasaun_id:  # membru ne'e tama organizasaun ne'e (hatama organizasaun la iha iha form membru)
			Membro.objects.filter(pk=self.membro_id, organizasaun__isnull=True).update(organizasaun_id=self.organizasaun_id)
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


class OrgPozisaun(models.Model):
	"""Posisi pada organigrama komisaun (misalnya Tezoreira, Seksaun Logistiku) beserta deskrisaun tarefas."""
	naran = models.CharField(max_length=150, verbose_name="Pozisaun")
	parent = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True, related_name='sub', verbose_name="Iha okos husi")
	urutan = models.PositiveSmallIntegerField(default=0, db_index=True, verbose_name="Nu. Urut")
	deskrisaun = models.TextField(blank=True, verbose_name="Deskrisaun Tarefas")  # satu baris = satu tarefa
	obs = models.TextField(blank=True, verbose_name="Observasaun")
	ativu = models.BooleanField(default=True, verbose_name="Ativu")

	class Meta:
		ordering = ['urutan', 'id']
		verbose_name = 'Pozisaun Organigrama'

	def tarefas(self):
		return [t.strip() for t in self.deskrisaun.splitlines() if t.strip()]

	def __str__(self):
		return self.naran


class OrgResponsavel(models.Model):
	"""Orang yang bertanggung jawab pada satu posisi organigrama; urutan 1 = koordinator (dicetak tebal)."""
	pozisaun = models.ForeignKey(OrgPozisaun, on_delete=models.CASCADE, related_name='responsavel')
	membro = models.ForeignKey(Membro, on_delete=models.SET_NULL, null=True, blank=True, related_name='+', verbose_name="Membru")
	naran = models.CharField(max_length=150, verbose_name="Naran")  # salinan nama; juga untuk yang bukan membru terdaftar
	kargu = models.CharField(max_length=80, blank=True, verbose_name="Kargu")  # contoh: Vice-Pres-1, Vice-Coord.
	urutan = models.PositiveSmallIntegerField(default=1, verbose_name="Nu. Urut")

	class Meta:
		ordering = ['urutan', 'id']
		verbose_name = 'Responsavel Organigrama'

	def __str__(self):
		return f'{self.naran} - {self.pozisaun}'


class Edukasaun(models.Model):
	"""Nivel edukasaun as-aas membru (baris ida de'it)."""
	NIVEL = [('Laiha', 'La eskola'), ('Primária', 'Eskola primária'), ('Pré-Sekundária', 'Eskola pré-sekundária'),
		('Sekundária', 'Eskola sekundária'), ('Diploma', 'Diploma'), ('Lisensiatura', 'Lisensiatura'),
		('Mestrado', 'Mestradu'), ('Doutoramentu', 'Doutoramentu')]
	membro = models.OneToOneField(Membro, on_delete=models.CASCADE, related_name='edukasaun')
	nivel = models.CharField(choices=NIVEL, max_length=15, db_index=True, verbose_name="Nivel Edukasaun")
	eskola = models.CharField(max_length=150, blank=True, verbose_name="Eskola / Universidade")
	area = models.CharField(max_length=120, blank=True, verbose_name="Área Estudu")
	tinan_remata = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Tinan Remata")

	class Meta:
		constraints = [models.CheckConstraint(condition=models.Q(nivel__in=[c[0] for c in [
			('Laiha', ''), ('Primária', ''), ('Pré-Sekundária', ''), ('Sekundária', ''), ('Diploma', ''), ('Lisensiatura', ''),
			('Mestrado', ''), ('Doutoramentu', '')]]), name='edukasaun_nivel_valid')]

	def resumu(self):
		extra = ', '.join(x for x in (self.eskola, self.area, str(self.tinan_remata or '')) if x)
		return f'{self.get_nivel_display()}' + (f' ({extra})' if extra else '')

	def __str__(self):
		return self.resumu()


class Servisu(models.Model):
	"""Servisu agora: iha servisu ka seidauk. Se iha servisu: fatin servisu (Governu, Organizasaun ka Kompañia), naran fatin no pozisaun;
	se seidauk: saida mak halo agora."""
	STATUS = [('Servisu', 'Iha servisu'), ('Seidauk', 'Seidauk iha servisu')]
	SETOR = [('Governu', 'Governu (instituisaun estadu)'), ('Organizasaun', 'Organizasaun (ONG, igreja ka asosiasaun)'),
		('Kompania', 'Kompañia (privadu ka negósiu)')]
	SETOR_BADAK = {'Governu': 'Governu', 'Organizasaun': 'Organizasaun', 'Kompania': 'Kompañia'}
	ATIVIDADE = [('Estudante', 'Estudante'), ('Hela uma', 'Hela iha uma no tau matan ba família'), ('Agrikultura', 'Agrikultór ka peskadór'),
		('Negosiu', "Halo negósiu ki'ik"), ('Dezempregadu', 'Buka hela servisu'), ('Aposentadu', 'Aposentadu'), ('Seluk', 'Seluk')]

	membro = models.OneToOneField(Membro, on_delete=models.CASCADE, related_name='servisu')
	status = models.CharField(choices=STATUS, max_length=10, db_index=True, verbose_name="Ita iha servisu ka lae?")
	setor = models.CharField(choices=SETOR, max_length=15, null=True, blank=True, db_index=True, verbose_name="Servisu iha ne'ebé?")
	instituisaun = models.CharField(max_length=150, blank=True, verbose_name="Naran fatin servisu")
	diresaun = models.CharField(max_length=120, blank=True, verbose_name="Diresaun ka departamentu")
	pozisaun = models.CharField(max_length=100, blank=True, verbose_name="Pozisaun ka kargu")
	kategoria = models.CharField(max_length=50, blank=True, verbose_name="Kategoria")
	grau = models.CharField(max_length=20, blank=True, verbose_name="Grau")
	data_hahu = models.DateField(null=True, blank=True, verbose_name="Data hahú servisu")
	municipality = models.ForeignKey('custom.Municipality', on_delete=models.PROTECT, null=True, blank=True, verbose_name="Munisípiu fatin servisu")
	atividade = models.CharField(choices=ATIVIDADE, max_length=15, null=True, blank=True, db_index=True, verbose_name="Ita halo saida agora?")
	detalle = models.CharField(max_length=200, blank=True, verbose_name="Esplikasaun badak")

	class Meta:
		constraints = [models.CheckConstraint(condition=models.Q(status__in=['Servisu', 'Seidauk']), name='servisu_status_valid')]

	def badak(self):
		"""Versaun badak ba kolua lista."""
		if self.status == 'Servisu':
			return f'{self.SETOR_BADAK.get(self.setor, "-")} · {self.pozisaun}'
		return f'Seidauk · {self.get_atividade_display() or "-"}'

	def resumu(self):
		"""Teks badak ba lista, historia no CSV."""
		if self.status == 'Servisu':
			nome = self.SETOR_BADAK.get(self.setor, '-')
			return f'{nome}: {self.instituisaun}, {self.pozisaun}'.strip(', ')
		return f'Seidauk servisu: {self.get_atividade_display() or "-"}' + (f' ({self.detalle})' if self.detalle else '')

	def __str__(self):
		return self.resumu()

