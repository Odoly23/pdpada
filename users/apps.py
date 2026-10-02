from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    def ready(self):
        from django.db.models.signals import post_migrate
        from users import signals  # noqa: F401
        from users.rbac import sync_after_migrate
        post_migrate.connect(sync_after_migrate, sender=self)
