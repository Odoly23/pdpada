from django.core.management.base import BaseCommand

from users.rbac import sync_groups


class Command(BaseCommand):
    help = 'Sinkroniza Group (papel) no Permission ho matriks RBAC iha config/roles.py.'

    def handle(self, *args, **opts):
        sync_groups()
        self.stdout.write(self.style.SUCCESS('RBAC sinkroniza ona.'))
