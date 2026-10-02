from django.conf import settings
from django.db import models
from django.utils import timezone


class ActiveManager(models.Manager):
    """Default manager: la inklui rejistu ne'ebé soft-delete ona."""
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class BaseModel(models.Model):
    # SET_NULL: hamoos user la hamoos dadus ne'ebé nia input (audit nafatin).
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, editable=False,
                                   on_delete=models.SET_NULL, related_name='%(app_label)s_%(class)s_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, editable=False,
                                   on_delete=models.SET_NULL, related_name='%(app_label)s_%(class)s_updated')
    updated_at = models.DateTimeField(auto_now=True)
    deleted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, editable=False,
                                   on_delete=models.SET_NULL, related_name='%(app_label)s_%(class)s_deleted')
    deleted_at = models.DateTimeField(null=True, blank=True, editable=False)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def soft_delete(self, user=None):
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=['deleted_at', 'deleted_by', 'updated_at'])

    def restore(self):
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['deleted_at', 'deleted_by', 'updated_at'])


class Municipality(BaseModel):
    code = models.CharField('Kódigu', max_length=5, unique=True)
    name = models.CharField('Naran', max_length=100, unique=True)

    class Meta:
        verbose_name = 'Munisípiu'
        verbose_name_plural = 'Munisípiu'
        ordering = ['name']

    def __str__(self):
        return self.name


class AdministrativePost(BaseModel):
    municipality = models.ForeignKey(Municipality, on_delete=models.PROTECT, related_name='posts',
                                     verbose_name='Munisípiu')
    name = models.CharField('Naran', max_length=100)

    class Meta:
        verbose_name = 'Postu Administrativu'
        verbose_name_plural = 'Postu Administrativu'
        ordering = ['municipality__name', 'name']
        constraints = [models.UniqueConstraint(fields=['municipality', 'name'], name='uniq_post_per_mun')]

    def __str__(self):
        return self.name


class Village(BaseModel):
    """Suku."""
    administrativepost = models.ForeignKey(AdministrativePost, on_delete=models.PROTECT,
                                           related_name='villages', verbose_name='Postu')
    name = models.CharField('Naran', max_length=100)

    class Meta:
        verbose_name = 'Suku'
        verbose_name_plural = 'Suku'
        ordering = ['administrativepost__name', 'name']
        constraints = [models.UniqueConstraint(fields=['administrativepost', 'name'], name='uniq_village_per_post')]

    def __str__(self):
        return self.name


class Aldeia(BaseModel):
    village = models.ForeignKey(Village, on_delete=models.PROTECT, related_name='aldeias',
                                verbose_name='Suku')
    name = models.CharField('Naran', max_length=100)

    class Meta:
        verbose_name = 'Aldeia'
        verbose_name_plural = 'Aldeia'
        ordering = ['village__name', 'name']
        constraints = [models.UniqueConstraint(fields=['village', 'name'], name='uniq_aldeia_per_village')]

    def __str__(self):
        return self.name

    @property
    def full_name(self):
        return f'{self.name}, {self.village.name}'
