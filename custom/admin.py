from django.contrib import admin

from custom.models import AdministrativePost, Aldeia, Municipality, Village


class BaseAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        if change:
            obj.updated_by = request.user
        else:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Municipality)
class MunicipalityAdmin(BaseAdmin):
    list_display = ('code', 'name')
    search_fields = ('name',)


@admin.register(AdministrativePost)
class PostAdmin(BaseAdmin):
    list_display = ('name', 'municipality')
    list_filter = ('municipality',)
    search_fields = ('name',)


@admin.register(Village)
class VillageAdmin(BaseAdmin):
    list_display = ('name', 'administrativepost')
    list_filter = ('administrativepost__municipality',)
    search_fields = ('name',)


@admin.register(Aldeia)
class AldeiaAdmin(BaseAdmin):
    list_display = ('name', 'village')
    list_filter = ('village__administrativepost__municipality',)
    search_fields = ('name', 'village__name')
