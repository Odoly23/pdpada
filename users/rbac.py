"""Sinkroniza Group + Permission ho matriks iha config.roles."""
from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission
from django.apps import apps

from config import roles as R


def sync_groups():
    # Permisaun kria iha post_migrate; garante existe ona molok atribui.
    for cfg in apps.get_app_configs():
        cfg.models_module and create_permissions(cfg, verbosity=0)
    for role, perms in R.ROLE_PERMISSIONS.items():
        group, _ = Group.objects.get_or_create(name=role)
        wanted = []
        for p in perms:
            app, code = p.split('.')
            wanted.append(Permission.objects.get(content_type__app_label=app, codename=code))
        group.permissions.set(wanted)


def sync_after_migrate(sender, **kwargs):
    sync_groups()
