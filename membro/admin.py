from django.contrib import admin

from custom.admin import BaseAdmin
from membro.models import Kargu, Membru, Organizasaun


@admin.register(Organizasaun)
class OrganizasaunAdmin(BaseAdmin):
    list_display = ('code', 'name')


@admin.register(Membru)
class MembruAdmin(BaseAdmin):
    list_display = ('naran', 'nu_eleitoral', 'aldeia', 'estadu')
    list_filter = ('estadu', 'sexu', 'aldeia__village__administrativepost')
    search_fields = ('naran', 'nu_eleitoral')
    autocomplete_fields = ()
    readonly_fields = ('public_id',)


@admin.register(Kargu)
class KarguAdmin(BaseAdmin):
    list_display = ('membru', 'tipu', 'nivel', 'postu', 'village', 'aldeia', 'is_active')
    list_filter = ('tipu', 'nivel', 'is_active')
