import uuid
from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from custom.models import AdministrativePost, Aldeia, BaseModel, Village

IDADE_MINIMA = 16


def foto_path(instance, filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'jpg'
    return f'membru/{instance.public_id}/{uuid.uuid4().hex}.{ext}'


def validate_foto_size(f):
    if f.size > settings.FOTO_MAX_BYTES:
        raise ValidationError(f'Foto boot liu (maksimu {settings.FOTO_MAX_BYTES // 1024 // 1024} MB).')


class Organizasaun(BaseModel):
    """OPD, OMD, DPD: organizasaun ne'ebé defende partidu (la hierarkia)."""
    code = models.CharField('Kódigu', max_length=10, unique=True)
    name = models.CharField('Naran', max_length=150)

    class Meta:
        verbose_name = 'Organizasaun'
        verbose_name_plural = 'Organizasaun'
        ordering = ['code']

    def __str__(self):
        return self.code


class Membru(BaseModel):
    class Sexu(models.TextChoices):
        MANE = 'M', 'Mane'
        FETO = 'F', 'Feto'

    class EstadoCivil(models.TextChoices):
        SOLTEIRO = 'solteiro', 'Solteiro/a'
        CASADO = 'casado', 'Casado/a'
        DIVORCIADO = 'divorciado', 'Divorciado/a'
        VIUVO = 'viuvo', 'Viuvo/a'

    class Edukasaun(models.TextChoices):
        LA_IHA = 'la_iha', 'La iha'
        BASIKU = 'basiku', 'Ensinu Báziku'
        SEKUNDARIU = 'sekundariu', 'Ensinu Sekundáriu'
        DIPLOMA = 'diploma', 'Diploma'
        LISENSIATURA = 'lisensiatura', 'Lisensiatura'
        MESTRADU = 'mestradu', 'Mestradu/Doutoramentu'

    class Estadu(models.TextChoices):
        REJISTADU = 'rejistadu', 'Rejistadu (Aldeia)'
        KONFIRMADU = 'konfirmadu', 'Konfirmadu (Suku)'
        APROVADU = 'aprovadu', 'Aprovadu (Postu)'

    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    nu_eleitoral = models.CharField(
        'Nu. Eleitoral', max_length=20,
        validators=[RegexValidator(r'^[A-Za-z0-9\-/]+$', 'De’it letra, numeru, "-" no "/".')])
    naran = models.CharField('Naran', max_length=200)
    fatin_moris = models.CharField('Fatin Moris', max_length=100, blank=True)
    data_moris = models.DateField('Data Moris')
    sexu = models.CharField('Sexu', max_length=1, choices=Sexu.choices)
    estadu_civil = models.CharField('Estadu Sivíl', max_length=12, choices=EstadoCivil.choices, blank=True)
    edukasaun = models.CharField('Nivel Edukasaun', max_length=15, choices=Edukasaun.choices, blank=True)
    okupasaun = models.CharField('Okupasaun', max_length=100, blank=True)
    telemovel = models.CharField('Nu. Telemovel', max_length=20, blank=True,
                                 validators=[RegexValidator(r'^\+?[0-9 ]{7,20}$', 'Nu. telemovel la loos.')])
    email = models.EmailField('Email', blank=True)
    enderesu = models.CharField('Enderesu', max_length=200, blank=True)
    foto = models.ImageField('Foto', upload_to=foto_path, blank=True,
                             validators=[FileExtensionValidator(['jpg', 'jpeg', 'png']), validate_foto_size])

    aldeia = models.ForeignKey(Aldeia, on_delete=models.PROTECT, related_name='membrus', verbose_name='Aldeia')
    organizasaun = models.ManyToManyField(Organizasaun, blank=True, related_name='membrus',
                                          verbose_name='Organizasaun (OPD/OMD/DPD)')

    estadu = models.CharField(max_length=12, choices=Estadu.choices, default=Estadu.REJISTADU, db_index=True)
    konfirma_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, editable=False,
                                    on_delete=models.SET_NULL, related_name='membru_konfirma')
    konfirma_at = models.DateTimeField(null=True, blank=True, editable=False)
    aprova_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, editable=False,
                                  on_delete=models.SET_NULL, related_name='membru_aprova')
    aprova_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        verbose_name = 'Membru'
        verbose_name_plural = 'Membru'
        ordering = ['naran']
        permissions = [
            ('confirm_membru', 'Bele konfirma membru (Suku)'),
            ('approve_membru', 'Bele aprova membru (Postu)'),
            ('view_report', 'Bele haree relatóriu/dashboard'),
        ]
        constraints = [
            # Nu. eleitoral úniku entre membru ativu (membru hamoos ona la bloqueia).
            models.UniqueConstraint(fields=['nu_eleitoral'], condition=Q(deleted_at__isnull=True),
                                    name='uniq_nu_eleitoral_active'),
        ]
        indexes = [models.Index(fields=['naran']), models.Index(fields=['aldeia', 'estadu'])]

    def __str__(self):
        return self.naran

    @property
    def idade(self):
        t = date.today()
        d = self.data_moris
        return t.year - d.year - ((t.month, t.day) < (d.month, d.day))

    @property
    def village(self):
        return self.aldeia.village

    @property
    def postu(self):
        return self.aldeia.village.administrativepost

    @property
    def is_locked(self):
        """Depois konfirma, Aldeia la bele edita tan."""
        return self.estadu != self.Estadu.REJISTADU

    def clean(self):
        super().clean()
        if self.data_moris:
            if self.data_moris > date.today():
                raise ValidationError({'data_moris': 'Data moris la bele iha futuru.'})
            if self.idade < IDADE_MINIMA:
                raise ValidationError({'data_moris': f'Idade tenke {IDADE_MINIMA} anos ba leten.'})

    def konfirma(self, user):
        if self.estadu != self.Estadu.REJISTADU:
            raise ValidationError('Membru ne’e la iha estadu "Rejistadu".')
        self.estadu, self.konfirma_by, self.konfirma_at = self.Estadu.KONFIRMADU, user, timezone.now()
        self.save(update_fields=['estadu', 'konfirma_by', 'konfirma_at', 'updated_at'])

    def aprova(self, user):
        if self.estadu != self.Estadu.KONFIRMADU:
            raise ValidationError('Membru tenke konfirma ona hosi Suku molok aprova.')
        self.estadu, self.aprova_by, self.aprova_at = self.Estadu.APROVADU, user, timezone.now()
        self.save(update_fields=['estadu', 'aprova_by', 'aprova_at', 'updated_at'])


class Kargu(BaseModel):
    """
    Pozisaun Coordenador / Sekjen iha nivel Postu, Suku ka Aldeia.
    Regra: wilayah ida iha Coordenador ida no Sekjen ida ativu.
    """
    class Nivel(models.TextChoices):
        POSTU = 'postu', 'Postu'
        SUKU = 'suku', 'Suku'
        ALDEIA = 'aldeia', 'Aldeia'

    class Tipu(models.TextChoices):
        COORDENADOR = 'coordenador', 'Coordenador'
        SEKJEN = 'sekjen', 'Sekjen'

    membru = models.ForeignKey(Membru, on_delete=models.PROTECT, related_name='kargus', verbose_name='Membru')
    tipu = models.CharField('Pozisaun', max_length=12, choices=Tipu.choices)
    nivel = models.CharField('Nivel', max_length=6, choices=Nivel.choices)
    postu = models.ForeignKey(AdministrativePost, null=True, blank=True, on_delete=models.PROTECT,
                              related_name='kargus', verbose_name='Postu')
    village = models.ForeignKey(Village, null=True, blank=True, on_delete=models.PROTECT,
                                related_name='kargus', verbose_name='Suku')
    aldeia = models.ForeignKey(Aldeia, null=True, blank=True, on_delete=models.PROTECT,
                               related_name='kargus', verbose_name='Aldeia')
    is_active = models.BooleanField('Ativu', default=True)
    data_hahu = models.DateField('Data hahu', null=True, blank=True)
    data_remata = models.DateField('Data remata', null=True, blank=True)

    class Meta:
        verbose_name = 'Kargu'
        verbose_name_plural = 'Kargu'
        ordering = ['nivel', 'tipu']
        constraints = [
            # Wilayah loos de'it tuir nivel (ida de'it mak prense).
            models.CheckConstraint(name='kargu_scope_matches_nivel', condition=(
                Q(nivel='postu', postu__isnull=False, village__isnull=True, aldeia__isnull=True) |
                Q(nivel='suku', postu__isnull=True, village__isnull=False, aldeia__isnull=True) |
                Q(nivel='aldeia', postu__isnull=True, village__isnull=True, aldeia__isnull=False))),
            # Coordenador/Sekjen ativu úniku ba wilayah ida.
            models.UniqueConstraint(fields=['tipu', 'postu'], name='uniq_kargu_postu',
                                    condition=Q(is_active=True, deleted_at__isnull=True, postu__isnull=False)),
            models.UniqueConstraint(fields=['tipu', 'village'], name='uniq_kargu_village',
                                    condition=Q(is_active=True, deleted_at__isnull=True, village__isnull=False)),
            models.UniqueConstraint(fields=['tipu', 'aldeia'], name='uniq_kargu_aldeia',
                                    condition=Q(is_active=True, deleted_at__isnull=True, aldeia__isnull=False)),
        ]

    def __str__(self):
        return f'{self.get_tipu_display()} {self.get_nivel_display()} {self.wilayah}: {self.membru}'

    @property
    def wilayah(self):
        return self.postu or self.village or self.aldeia

    def clean(self):
        super().clean()
        wanted = {'postu': self.postu_id, 'suku': self.village_id, 'aldeia': self.aldeia_id}
        if not wanted.get(self.nivel) or sum(bool(v) for v in wanted.values()) != 1:
            raise ValidationError(f'Prense de’it wilayah ba nivel {self.nivel}.')
        if self.membru_id:
            a = self.membru.aldeia
            ok = {
                'aldeia': self.aldeia_id == a.id,
                'suku': self.village_id == a.village_id,
                'postu': self.postu_id == a.village.administrativepost_id,
            }[self.nivel]
            if not ok:
                raise ValidationError('Membru tenke hela iha wilayah ne’ebé nia koordena.')
        if self.data_hahu and self.data_remata and self.data_remata < self.data_hahu:
            raise ValidationError({'data_remata': 'Data remata la bele molok data hahu.'})
