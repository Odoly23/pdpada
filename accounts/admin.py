from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class StaffUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("APORTIL", {"fields": ("preferred_language", "operator", "phone")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("APORTIL", {"fields": ("preferred_language", "operator", "phone")}),)
    list_display = ("username", "get_full_name", "operator", "is_active", "last_login")
    list_filter = ("groups", "is_active", "operator")
