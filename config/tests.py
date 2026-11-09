from io import StringIO
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from custom.models import Village
from membro.models import Membro


class SeedDemoTests(TestCase):
	def run_cmd(self, *args):
		out = StringIO()
		call_command(*args, stdout=out)
		return out.getvalue()

	def setUp(self):
		self.run_cmd('seed_inisial')

	def test_requires_strong_password(self):
		with self.assertRaises(CommandError):
			call_command('seed_demo', stdout=StringIO())
		with self.assertRaises(CommandError):
			call_command('seed_demo', '--password', '12345678', stdout=StringIO())
		self.assertFalse(Membro.objects.exists())

	def test_create_and_remove(self):
		self.run_cmd('seed_demo', '--password', 'Demo-Aman-2026!', '--jumlah', '20')
		self.assertEqual(Membro.objects.count(), 20)
		self.assertEqual(Village.objects.filter(name__startswith='Suku Demo').count(), 3)
		u = User.objects.get(username='demo_sekrsuku')
		self.assertTrue(u.check_password('Demo-Aman-2026!'))
		self.assertEqual(u.scope.village.name, 'Suku Demo 1')
		with self.assertRaises(CommandError):
			call_command('seed_demo', '--password', 'Demo-Aman-2026!', stdout=StringIO())
		self.run_cmd('seed_demo', '--hapus')
		self.assertFalse(Membro.objects.exists())
		self.assertFalse(User.objects.filter(username__startswith='demo_').exists())
		self.assertFalse(Village.objects.filter(name__startswith='Suku Demo').exists())
		self.assertTrue(User.objects.filter(username='admin').exists())
