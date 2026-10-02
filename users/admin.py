from django.contrib import admin

from users.models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'postu', 'village', 'aldeia', 'organizasaun', 'must_change_password')
    raw_id_fields = ('user', 'membru')
