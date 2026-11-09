import datetime
import random
from django.contrib.auth.models import Group, User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from config import roles
from custom.models import AdministrativePost, Village, Aldeia, Organizasaun, Year
from membro.models import Membro, Alokasaun, Historia
from membro.utils import log_historia
from users.models import UserScope

PREFIX = 'DEMO'
USERS = [
	('demo_presidente', roles.PRESIDENTE, {}),
	('demo_koordpostu', roles.KOORD_POSTU, {}),
	('demo_sekrpostu', roles.SEKR_POSTU, {}),
	('demo_koordsuku', roles.KOORD_SUKU, {'v': 0}),
	('demo_sekrsuku', roles.SEKR_SUKU, {'v': 0}),
	('demo_sekraldeia', roles.SEKR_ALDEIA, {'a': 0}),
	('demo_koordorg', roles.KOORD_ORG, {'o': 'OJD'}),
	('demo_sekrorg', roles.SEKR_ORG, {'o': 'OJD'}),
]
NAMA = ['Joao', 'Maria', 'Jose', 'Ana', 'Pedro', 'Lucia', 'Antonio', 'Rosa', 'Tomas', 'Marta', 'Carlos', 'Julia',
	'Paulo', 'Sandra', 'Miguel', 'Elena', 'Domingos', 'Teresa', 'Armando', 'Filomena']
APELIDU = ['Pereira', 'da Silva', 'Soares', 'Gomes', 'Ximenes', 'Belo', 'Guterres', 'Amaral', 'Lopes', 'Cruz',
	'Martins', 'Fernandes', 'Costa', 'Alves', 'Carvalho']


class Command(BaseCommand):
	help = ('Data DEMO fiktif untuk presentasi (suku/aldeia/membru/user demo_*). '
		'Wajib --password. Hapus semuanya dengan --hapus.')

	def add_arguments(self, parser):
		parser.add_argument('--password', help='Password untuk semua user demo_*')
		parser.add_argument('--jumlah', type=int, default=60, help='Jumlah membru demo (default 60)')
		parser.add_argument('--hapus', action='store_true', help='Hapus semua data demo')

	def handle(self, *args, **opts):
		if opts['hapus']:
			return self.hapus()
		password = opts['password']
		if not password:
			raise CommandError('Wajib isi --password untuk user demo.')
		try:
			validate_password(password)
		except ValidationError as e:
			raise CommandError('Password lemah: ' + ' '.join(e.messages))
		if not Group.objects.filter(name=roles.PRESIDENTE).exists() or not Year.objects.filter(is_active=True).exists():
			raise CommandError('Jalankan `python manage.py seed_inisial` dulu.')
		if Membro.objects.filter(nu_eleitoral__startswith=PREFIX).exists():
			raise CommandError('Data demo sudah ada. Pakai --hapus dulu jika ingin membuat ulang.')

		rnd = random.Random(2026)
		post = AdministrativePost.objects.order_by('id').first()
		year = Year.objects.get(is_active=True)
		orgs = list(Organizasaun.objects.filter(is_active=True))
		villages, aldeias = [], []
		for i in range(1, 4):
			v, _ = Village.objects.get_or_create(administrativepost=post, name=f'Suku Demo {i}')
			villages.append(v)
			for j in range(1, 4):
				a, _ = Aldeia.objects.get_or_create(village=v, name=f'Aldeia Demo {i}.{j}')
				aldeias.append(a)

		creator = None
		for username, role, sc in USERS:
			u, created = User.objects.get_or_create(username=username, defaults={'first_name': username.replace('demo_', '').title()})
			u.set_password(password)
			u.save()
			u.groups.set([Group.objects.get(name=role)])
			UserScope.objects.update_or_create(user=u, defaults={
				'village': villages[sc['v']] if 'v' in sc else (aldeias[sc['a']].village if 'a' in sc else None),
				'aldeia': aldeias[sc['a']] if 'a' in sc else None,
				'organizasaun': next((o for o in orgs if o.code == sc['o']), None) if 'o' in sc else None,
			})
			if username == 'demo_sekrsuku':
				creator = u

		pesos = ['Aprovadu'] * 6 + ['Pendente'] * 3 + ['Rejeitadu']
		for n in range(1, opts['jumlah'] + 1):
			a = rnd.choice(aldeias)
			sex = rnd.choice(['Mane', 'Feto'])
			apr = rnd.choice(pesos)
			m = Membro.objects.create(
				nome=f'{rnd.choice(NAMA)} {rnd.choice(APELIDU)}', sex=sex,
				date_of_birth=datetime.date(rnd.randint(1960, 2006), rnd.randint(1, 12), rnd.randint(1, 28)),
				marital=rnd.choice(['Solteiro/a', 'Casado/a', 'Casado/a', 'Viuvo/a']),
				nu_eleitoral=f'{PREFIX}{n:05d}', village=a.village, aldeia=a,
				organizasaun=rnd.choice(orgs + [None, None]) if orgs else None,
				data_hakbit=datetime.date(rnd.randint(2010, 2025), 1, 1),
				status=rnd.choice(['Ativu'] * 8 + ['Inativu']), aprovasaun=apr, year=year,
				razaun_rejeita='Dokumentu la kompletu' if apr == 'Rejeitadu' else None,
				datetime=timezone.now(), user=creator)
			log_historia(creator, m, 'Kria', f'Data demo: {m}')

		hoje = datetime.date.today()
		aprovadus = list(Membro.objects.filter(nu_eleitoral__startswith=PREFIX, aprovasaun='Aprovadu', status='Ativu'))
		for poz, nivel in [('Presidente', 'Postu'), ('Coordenador', 'Postu'), ('Sekretariu', 'Postu')]:
			Alokasaun.objects.create(membro=rnd.choice(aprovadus), nivel=nivel, pozisaun=poz, data_hahu=hoje, user=creator)
		for v in villages:
			cand = [m for m in aprovadus if m.village_id == v.pk]
			for poz, m in zip(['Coordenador', 'Sekretariu'], rnd.sample(cand, min(2, len(cand)))):
				Alokasaun.objects.create(membro=m, nivel='Suku', pozisaun=poz, village=v, data_hahu=hoje, user=creator)
		self.stdout.write(self.style.SUCCESS(
			f'Data demo dibuat: {opts["jumlah"]} membru, 3 suku, 9 aldeia, {len(USERS)} user (demo_*).'))
		self.stdout.write('Hapus semua: python manage.py seed_demo --hapus')

	def hapus(self):
		Historia.objects.filter(membro_nome__contains=PREFIX).delete()
		n = Membro.objects.filter(nu_eleitoral__startswith=PREFIX).delete()[0]
		User.objects.filter(username__startswith='demo_').delete()
		Aldeia.objects.filter(name__startswith='Aldeia Demo', membro__isnull=True).delete()
		Village.objects.filter(name__startswith='Suku Demo', aldeia__isnull=True, membro__isnull=True).delete()
		self.stdout.write(self.style.SUCCESS(f'Data demo dihapus ({n} rekaman terkait membru).'))
