from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from config import roles as R


class Profile(models.Model):
    """
    Eskopu user: papel mai husi Django Group (RBAC), wilayah/organizasaun mai husi ne'e.
    Fonte úniku ba "user ne'e bele haree dadus saida" (haree config.scope).
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    membru = models.ForeignKey('membro.Membru', null=True, blank=True, on_delete=models.SET_NULL,
                               related_name='profiles', verbose_name='Membru')
    postu = models.ForeignKey('custom.AdministrativePost', null=True, blank=True, on_delete=models.PROTECT,
                              verbose_name='Postu')
    village = models.ForeignKey('custom.Village', null=True, blank=True, on_delete=models.PROTECT,
                                verbose_name='Suku')
    aldeia = models.ForeignKey('custom.Aldeia', null=True, blank=True, on_delete=models.PROTECT,
                               verbose_name='Aldeia')
    organizasaun = models.ForeignKey('membro.Organizasaun', null=True, blank=True, on_delete=models.PROTECT,
                                     verbose_name='Organizasaun')
    must_change_password = models.BooleanField(default=True)

    class Meta:
        permissions = [('manage_users', 'Bele jere user no papel')]

    def __str__(self):
        return f'Profile {self.user}'


SCOPE_FIELD_BY_ROLE = {
    R.POSTU: 'postu', R.SUKU: 'village', R.ALDEIA: 'aldeia',
    R.OPD: 'organizasaun', R.OMD: 'organizasaun', R.DPD: 'organizasaun',
}


def validate_scope(role, profile_data):
    """Papel territorial/organizasaun tenke iha eskopu; papel global la iha."""
    needed = SCOPE_FIELD_BY_ROLE.get(role)
    if needed and not profile_data.get(needed):
        raise ValidationError({needed: 'Eskopu obrigatóriu ba papel ne’e.'})
