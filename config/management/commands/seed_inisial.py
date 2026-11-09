import os
import secrets
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.utils import timezone
from config import roles
from custom.models import Municipality, AdministrativePost, Organizasaun, Year


class Command(BaseCommand):
	help = 'Isi data inisial: peran (group), Dili/Dom Aleixo, OJD/OPD/MPD, tinan ativu no user admin.'

	def handle(self, *args, **options):
		for key, _ in roles.ROLE_LABELS:
			Group.objects.get_or_create(name=key)
		mun, _ = Municipality.objects.get_or_create(name='Dili', defaults={'code': 'DI'})
		AdministrativePost.objects.get_or_create(municipality=mun, name='Dom Aleixo')
		for code in ['OJD', 'OPD', 'MPD']:
			Organizasaun.objects.get_or_create(code=code, defaults={'name': code})
		if not Year.objects.exists():
			Year.objects.create(year=timezone.now().year, is_active=True)
		user = User.objects.filter(username='admin').first()
		if not user:
			password = os.environ.get('ADMIN_PASSWORD') or secrets.token_urlsafe(12)
			user = User.objects.create_user('admin', password=password, first_name='Administrador')
			user.groups.add(Group.objects.get(name=roles.ADMIN))
			if not os.environ.get('ADMIN_PASSWORD'):
				self.stdout.write(self.style.WARNING(f'User admin dibuat. Password: {password}  (catat, hanya tampil sekali)'))
			else:
				self.stdout.write('User admin dibuat dengan ADMIN_PASSWORD.')
		self.stdout.write(self.style.SUCCESS('Seed inisial selesai.'))
