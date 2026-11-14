import io
import shutil
import tempfile
from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
from config import roles
from custom.models import Municipality, AdministrativePost, Village, Aldeia, Year
from eleisaun.models import Eleisaun, TempatVoting, FiskaisTempat, Resultado
from membro.models import Membro, Historia
from users.models import UserScope

TMP = tempfile.mkdtemp(prefix='pdpada-eleisaun-')


def jpeg(color=(200, 30, 30)):
	buf = io.BytesIO()
	Image.new('RGB', (120, 80), color).save(buf, 'JPEG')
	return SimpleUploadedFile('foto.jpg', buf.getvalue(), content_type='image/jpeg')


@override_settings(PRIVATE_ROOT=TMP)
class EleisaunBase(TestCase):
	@classmethod
	def setUpTestData(cls):
		for key, _ in roles.ROLE_LABELS:
			Group.objects.get_or_create(name=key)
		mun = Municipality.objects.create(name='Dili')
		post = AdministrativePost.objects.create(municipality=mun, name='Dom Aleixo')
		cls.va = Village.objects.create(administrativepost=post, name='Suku A')
		cls.vb = Village.objects.create(administrativepost=post, name='Suku B')
		cls.a1 = Aldeia.objects.create(village=cls.va, name='A1')
		cls.b1 = Aldeia.objects.create(village=cls.vb, name='B1')
		cls.year = Year.objects.create(year=2026, is_active=True)
		cls.users = {}
		for name, role in [('presidente', roles.PRESIDENTE), ('sekrpostu', roles.SEKR_POSTU), ('koordsuku', roles.KOORD_SUKU),
				('admin', roles.ADMIN), ('fiskais1', roles.FISKAIS), ('fiskais2', roles.FISKAIS)]:
			u = User.objects.create_user(name, password='Teste-12345!')
			u.groups.add(Group.objects.get(name=role))
			UserScope.objects.create(user=u, village=cls.va if name == 'koordsuku' else None)
			cls.users[name] = u
		cls.t1 = TempatVoting.objects.create(naran='Eskola A', village=cls.va, aldeia=cls.a1)
		cls.t2 = TempatVoting.objects.create(naran='Eskola B', village=cls.vb)
		FiskaisTempat.objects.create(user=cls.users['fiskais1'], tempat=cls.t1)
		FiskaisTempat.objects.create(user=cls.users['fiskais2'], tempat=cls.t2)
		for i in range(10):
			Membro.objects.create(nome=f'M{i}', sex='Mane', date_of_birth='1990-01-01', nu_eleitoral=f'EL{i:05d}', village=cls.va if i < 6 else cls.vb,
				aldeia=cls.a1 if i < 6 else cls.b1, year=cls.year, user=cls.users['admin'])

	@classmethod
	def tearDownClass(cls):
		super().tearDownClass()
		shutil.rmtree(TMP, ignore_errors=True)

	def login(self, name):
		self.client.logout()
		self.assertTrue(self.client.login(username=name, password='Teste-12345!'))

	def live(self, ativu=True):
		return Eleisaun.objects.create(naran='Eleisaun Postu', tinan=2026, ativu=ativu)

	def submit(self, **kw):
		data = {'votos_partidu': 40, 'foto': jpeg()}
		data.update(kw)
		return self.client.post(reverse('eleisaun-input'), data)


class FiskaisInputTests(EleisaunBase):
	def test_only_fiskais_open_the_input_page(self):
		self.live()
		for u, code in [('fiskais1', 200), ('presidente', 403), ('admin', 403), ('koordsuku', 403), ('sekrpostu', 403)]:
			self.login(u)
			self.assertEqual(self.client.get(reverse('eleisaun-input')).status_code, code, u)

	def test_fiskais_has_no_access_to_member_data_or_dashboard(self):
		self.login('fiskais1')
		for name in ('membro-list', 'membro-painel', 'eleisaun-live', 'eleisaun-live-data', 'eleisaun-komparasaun', 'eleisaun-admin', 'report-dash'):
			self.assertEqual(self.client.get(reverse(name)).status_code, 403, name)

	def test_submit_once_then_form_is_locked(self):
		self.live()
		self.login('fiskais1')
		resp = self.submit()
		self.assertRedirects(resp, reverse('eleisaun-input'))
		r = Resultado.objects.get()
		self.assertEqual((r.tempat, r.votos_partidu, r.submetidu, r.submetidu_husi), (self.t1, 40, True, self.users['fiskais1']))
		page = self.client.get(reverse('eleisaun-input'))
		self.assertTrue(page.context['locked'])
		self.assertContains(page, 'Rezultadu submete ona')
		self.assertIsNone(page.context['form'])
		self.submit(votos_partidu=999)  # percobaan kedua ditolak
		r.refresh_from_db()
		self.assertEqual(r.votos_partidu, 40)
		self.assertEqual(Resultado.objects.count(), 1)
		self.assertTrue(Historia.objects.filter(aksaun='Resultado Submete').exists())

	def test_admin_reopens_then_fiskais_can_correct_once_more(self):
		self.live()
		self.login('fiskais1')
		self.submit()
		r = Resultado.objects.get()
		self.login('fiskais1')
		self.assertEqual(self.client.post(reverse('resultado-loke', args=[r.pk])).status_code, 403)  # fiskais tidak bisa buka sendiri
		self.login('admin')
		self.client.post(reverse('resultado-loke', args=[r.pk]))
		r.refresh_from_db()
		self.assertFalse(r.submetidu)
		self.login('fiskais1')
		page = self.client.get(reverse('eleisaun-input'))
		self.assertFalse(page.context['locked'])
		self.assertEqual(page.context['form'].instance.votos_partidu, 40)  # data lama tetap ada
		self.client.post(reverse('eleisaun-input'), {'votos_partidu': 55})  # foto lama tidak perlu diunggah ulang
		r.refresh_from_db()
		self.assertEqual((r.votos_partidu, r.submetidu), (55, True))
		self.assertTrue(Historia.objects.filter(aksaun='Loke Resultado').exists())

	def test_no_active_eleisaun_blocks_input(self):
		self.login('fiskais1')
		page = self.client.get(reverse('eleisaun-input'))
		self.assertContains(page, 'Laiha eleisaun ativu')
		self.submit()
		self.assertEqual(Resultado.objects.count(), 0)

	def test_fiskais_without_tempat_gets_notice(self):
		self.live()
		FiskaisTempat.objects.filter(user=self.users['fiskais1']).delete()
		self.login('fiskais1')
		self.assertContains(self.client.get(reverse('eleisaun-input')), 'seidauk hetan tempat')

	def test_form_has_only_votes_and_photo_and_tempat_is_automatic(self):
		self.live()
		self.login('fiskais1')
		page = self.client.get(reverse('eleisaun-input'))
		self.assertEqual(list(page.context['form'].fields), ['votos_partidu', 'foto'])
		self.assertContains(page, 'ESKOLA A')  # tempat dari penugasan Admin
		self.assertNotContains(page, 'name="tempat"')
		self.submit(tempat=self.t2.pk)  # tempat tidak bisa dipilih sendiri
		self.assertEqual(Resultado.objects.get().tempat, self.t1)

	def test_photo_is_validated_and_both_fields_required(self):
		self.live()
		self.login('fiskais1')
		bad_img = SimpleUploadedFile('x.jpg', b'bukan gambar', content_type='image/jpeg')
		self.assertEqual(self.submit(foto=bad_img).status_code, 200)
		pdf_as_photo = SimpleUploadedFile('x.pdf', b'%PDF-1.4 palsu', content_type='application/pdf')
		self.assertEqual(self.submit(foto=pdf_as_photo).status_code, 200)
		self.assertEqual(self.client.post(reverse('eleisaun-input'), {'votos_partidu': 5}).status_code, 200)  # tanpa foto
		self.assertEqual(self.client.post(reverse('eleisaun-input'), {'foto': jpeg()}).status_code, 200)  # tanpa votu
		self.assertEqual(Resultado.objects.count(), 0)

	def test_uploaded_photo_is_reencoded_and_stored_privately(self):
		self.live()
		self.login('fiskais1')
		self.submit()
		r = Resultado.objects.get()
		self.assertRegex(r.foto.name, r'^resultado/[0-9a-f]{64}\.jpg$')
		with self.assertRaises(ValueError):
			r.foto.url  # tanpa URL publik

	def test_file_access_owner_postu_only(self):
		self.live()
		self.login('fiskais1')
		self.submit()
		r = Resultado.objects.get()
		for u, code in [('fiskais1', 200), ('presidente', 200), ('sekrpostu', 200), ('fiskais2', 404), ('koordsuku', 403), ('admin', 403)]:
			self.login(u)
			resp = self.client.get(reverse('eleisaun-file', args=[r.pk, 'foto']))
			self.assertEqual(resp.status_code, code, u)
		self.login('presidente')
		resp = self.client.get(reverse('eleisaun-file', args=[r.pk, 'foto']))
		self.assertEqual((resp['Content-Type'], resp['Cache-Control']), ('image/jpeg', 'private, no-store'))
		self.assertEqual(self.client.get(reverse('eleisaun-file', args=[r.pk, 'formulariu'])).status_code, 404)  # PDF tidak ada lagi


class LiveDashboardTests(EleisaunBase):
	def test_closed_when_no_active_eleisaun(self):
		self.live(ativu=False)
		self.login('presidente')
		self.assertEqual(self.client.get(reverse('eleisaun-live-data')).json(), {'ativu': False})

	def test_live_page_is_standalone_fullscreen_with_clock_and_wake_lock(self):
		self.login('presidente')
		resp = self.client.get(reverse('eleisaun-live'))
		for needle in ('requestFullscreen', 'wakeLock', 'id="clock"', 'rotate(', 'live.css', 'js_custom/highcharts.js', 'noindex', 'setInterval(load, 10000)',
				'<title>SGDM-PDPADA - Live Dashboard Eleisaun</title>', 'name="description"'):
			self.assertContains(resp, needle)
		self.assertNotContains(resp, 'main-navbar')  # tanpa menu: layar penuh
		self.assertNotContains(resp, 'https://')
		self.assertNotContains(resp, 'innerHTML')  # nama tempat dipasang aman lewat textContent

	def test_payload_counts_only_submitted_results(self):
		el = self.live()
		Resultado.objects.create(eleisaun=el, tempat=self.t1, votos_partidu=40, submetidu=True)
		Resultado.objects.create(eleisaun=el, tempat=self.t2, votos_partidu=99, submetidu=False)  # dibuka kembali: tidak dihitung
		self.login('presidente')
		j = self.client.get(reverse('eleisaun-live-data')).json()
		self.assertEqual(j['kpi'], {'votos': 40, 'membru': 10, 'persentajen': 400.0, 'submetidu': 1, 'tempat': 2,
			'kompara': {'kode': 'liu', 'label': 'Liu total dadus', 'diferensa': 30}})
		self.assertEqual({t['tempat']: (t['votos'], t['submetidu']) for t in j['tempat']}, {'Eskola A': (40, True), 'Eskola B': (0, False)})
		self.assertEqual(self.client.get(reverse('eleisaun-live-data'))['Cache-Control'], 'no-store')

	def test_payload_has_no_personal_data(self):
		self.live()
		self.login('presidente')
		raw = self.client.get(reverse('eleisaun-live-data')).content.decode()
		for secret in ('EL00001', 'M1', 'fiskais1', 'nu_eleitoral'):
			self.assertNotIn(secret, raw)

	def test_only_one_live_eleisaun_and_admin_toggle(self):
		a = Eleisaun.objects.create(naran='Lama', tinan=2021, ativu=True)
		b = Eleisaun.objects.create(naran='Foun', tinan=2026, ativu=True)
		a.refresh_from_db()
		self.assertFalse(a.ativu)
		self.assertTrue(b.ativu)
		self.login('admin')
		self.client.post(reverse('eleisaun-toggle', args=[b.pk]))
		b.refresh_from_db()
		self.assertFalse(b.ativu)  # dashboard taka
		self.client.post(reverse('eleisaun-toggle', args=[a.pk]))
		a.refresh_from_db()
		self.assertTrue(a.ativu)
		self.assertEqual(self.client.get(reverse('eleisaun-toggle', args=[a.pk])).status_code, 405)
		self.assertTrue(Historia.objects.filter(aksaun='Eleisaun Live').exists())

	def test_dashboard_roles(self):
		self.live()
		for u, code in [('presidente', 200), ('sekrpostu', 200), ('koordsuku', 200), ('admin', 403), ('fiskais1', 403)]:
			self.login(u)
			self.assertEqual(self.client.get(reverse('eleisaun-live')).status_code, code, u)
			self.assertEqual(self.client.get(reverse('eleisaun-live-data')).status_code, code, u)
		self.client.logout()
		self.assertEqual(self.client.get(reverse('eleisaun-live')).status_code, 302)


class KomparasaunTests(EleisaunBase):
	def test_compares_members_and_votes_per_suku(self):
		el = self.live()
		Resultado.objects.create(eleisaun=el, tempat=self.t1, votos_partidu=4, submetidu=True)
		Resultado.objects.create(eleisaun=el, tempat=self.t2, votos_partidu=5, submetidu=True)
		self.login('presidente')
		resp = self.client.get(reverse('eleisaun-komparasaun'))
		self.assertEqual([(r['suku'], r['membru'], r['votos'], r['persentajen']) for r in resp.context['rows']], [('Suku A', 6, 4, 66.7), ('Suku B', 4, 5, 125.0)])
		t = resp.context['totals']
		self.assertEqual((t['membru'], t['votos'], t['persentajen'], t['diferensa'], t['submetidu'], t['tempat']), (10, 9, 90.0, -1, 2, 2))
		self.assertContains(resp, 'chart_kompara')
		self.assertNotContains(resp, 'https://')

	def test_without_eleisaun_shows_zero_votes(self):
		self.login('presidente')
		resp = self.client.get(reverse('eleisaun-komparasaun'))
		self.assertEqual(resp.context['totals']['votos'], 0)
		self.assertContains(resp, 'LAIHA ELEISAUN ATIVU')

	def test_roles(self):
		for u, code in [('presidente', 200), ('sekrpostu', 200), ('koordsuku', 403), ('admin', 403), ('fiskais1', 403)]:
			self.login(u)
			self.assertEqual(self.client.get(reverse('eleisaun-komparasaun')).status_code, code, u)


class AdminManagementTests(EleisaunBase):
	def test_only_admin_manages(self):
		for name in ('eleisaun-admin', 'eleisaun-add', 'tempat-add', 'fiskais-add'):
			for u in ('presidente', 'fiskais1', 'koordsuku'):
				self.login(u)
				self.assertEqual(self.client.get(reverse(name)).status_code, 403, (name, u))
			self.login('admin')
			self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

	def test_admin_adds_eleisaun_tempat_and_assigns_fiskais(self):
		self.login('admin')
		self.client.post(reverse('eleisaun-add'), {'naran': 'Eleisaun 2031', 'tinan': 2031})
		self.assertTrue(Eleisaun.objects.filter(tinan=2031, ativu=False).exists())
		self.client.post(reverse('tempat-add'), {'naran': 'Eskola C', 'village': self.va.pk, 'aldeia': self.a1.pk, 'ativu': 'on'})
		tempat = TempatVoting.objects.get(naran='Eskola C')
		novo = User.objects.create_user('fiskais3', password='Teste-12345!')
		novo.groups.add(Group.objects.get(name=roles.FISKAIS))
		self.client.post(reverse('fiskais-add'), {'user': novo.pk, 'tempat': tempat.pk})
		self.assertEqual(FiskaisTempat.objects.get(user=novo).tempat, tempat)

	def test_tempat_aldeia_must_belong_to_suku(self):
		self.login('admin')
		resp = self.client.post(reverse('tempat-add'), {'naran': 'Eskola X', 'village': self.va.pk, 'aldeia': self.b1.pk, 'ativu': 'on'})
		self.assertContains(resp, "la hela iha suku ne&#x27;e")
		self.assertFalse(TempatVoting.objects.filter(naran='Eskola X').exists())

	def test_fiskais_choices_exclude_non_fiskais_and_already_assigned(self):
		self.login('admin')
		names = set(self.client.get(reverse('fiskais-add')).context['form'].fields['user'].queryset.values_list('username', flat=True))
		self.assertEqual(names, set())  # fiskais1 dan fiskais2 sudah ditugaskan, peran lain tidak masuk
		FiskaisTempat.objects.filter(user=self.users['fiskais1']).delete()
		names = set(self.client.get(reverse('fiskais-add')).context['form'].fields['user'].queryset.values_list('username', flat=True))
		self.assertEqual(names, {'fiskais1'})

	def test_admin_cannot_see_member_data_and_admin_page_lists_results(self):
		el = self.live()
		Resultado.objects.create(eleisaun=el, tempat=self.t1, votos_partidu=7, submetidu=True, submetidu_husi=self.users['fiskais1'])
		self.login('admin')
		page = self.client.get(reverse('eleisaun-admin'))
		self.assertContains(page, 'Loke Fali')
		self.assertContains(page, 'Eskola A')
		self.assertEqual(self.client.get(reverse('membro-list')).status_code, 403)

	def test_delete_fiskais_assignment_post_only(self):
		self.login('admin')
		fk = FiskaisTempat.objects.get(user=self.users['fiskais1'])
		self.assertEqual(self.client.get(reverse('fiskais-del', args=[fk.pk])).status_code, 405)
		self.client.post(reverse('fiskais-del', args=[fk.pk]))
		self.assertFalse(FiskaisTempat.objects.filter(pk=fk.pk).exists())


class MenuTests(EleisaunBase):
	def test_menu_per_role(self):
		self.login('fiskais1')
		html = self.client.get(reverse('home')).content.decode()
		self.assertIn(reverse('eleisaun-input'), html)
		self.assertNotIn(reverse('membro-list'), html)
		self.login('presidente')
		html = self.client.get(reverse('home')).content.decode()
		for name in ('eleisaun-live', 'eleisaun-komparasaun'):
			self.assertIn(reverse(name), html)
		self.login('koordsuku')
		html = self.client.get(reverse('home')).content.decode()
		self.assertIn(reverse('eleisaun-live'), html)
		self.assertNotIn(reverse('eleisaun-komparasaun'), html)
		self.login('admin')
		self.assertIn(reverse('eleisaun-admin'), self.client.get(reverse('user-painel')).content.decode())


class KomparaLabelTests(EleisaunBase):
	"""Label perbandingan votu PD dengan total membru, dalam Tetun INL."""
	def hasil(self, v1, v2):
		el = self.live()
		Resultado.objects.create(eleisaun=el, tempat=self.t1, votos_partidu=v1, submetidu=True)
		Resultado.objects.create(eleisaun=el, tempat=self.t2, votos_partidu=v2, submetidu=True)
		self.login('presidente')

	def test_helper_three_states(self):
		from eleisaun.utils import kompara
		self.assertEqual(kompara(3, 10), {'kode': 'menus', 'label': 'Menus husi total dadus', 'diferensa': -7})
		self.assertEqual(kompara(15, 10), {'kode': 'liu', 'label': 'Liu total dadus', 'diferensa': 5})
		self.assertEqual(kompara(10, 10), {'kode': 'hanesan', 'label': 'Hanesan ho total dadus', 'diferensa': 0})

	def test_less_than_total_members_label(self):
		self.hasil(3, 4)  # 7 votu, 10 membru
		resp = self.client.get(reverse('eleisaun-komparasaun'))
		self.assertEqual(resp.context['totals']['kompara']['kode'], 'menus')
		self.assertContains(resp, 'Menus husi total dadus')
		self.assertNotContains(resp, 'Liu total dadus')
		self.assertEqual(self.client.get(reverse('eleisaun-live-data')).json()['kpi']['kompara']['label'], 'Menus husi total dadus')

	def test_more_than_total_members_label(self):
		self.hasil(10, 5)  # 15 votu, 10 membru
		resp = self.client.get(reverse('eleisaun-komparasaun'))
		self.assertEqual(resp.context['totals']['kompara']['kode'], 'liu')
		self.assertContains(resp, 'Liu total dadus')
		self.assertContains(resp, '+5')
		self.assertEqual(self.client.get(reverse('eleisaun-live-data')).json()['kpi']['kompara']['kode'], 'liu')

	def test_equal_label_and_per_suku_labels(self):
		self.hasil(6, 4)  # Suku A: 6 votu vs 6 membru; Suku B: 4 votu vs 4 membru
		resp = self.client.get(reverse('eleisaun-komparasaun'))
		self.assertEqual([r['kompara']['kode'] for r in resp.context['rows']], ['hanesan', 'hanesan'])
		self.assertEqual(resp.context['totals']['kompara']['label'], 'Hanesan ho total dadus')

	def test_labels_can_differ_per_suku(self):
		self.hasil(2, 9)  # Suku A: 2 vs 6 menus; Suku B: 9 vs 4 liu
		rows = self.client.get(reverse('eleisaun-komparasaun')).context['rows']
		self.assertEqual([r['kompara']['kode'] for r in rows], ['menus', 'liu'])

	def test_live_page_shows_label_element_and_handler(self):
		self.live()
		self.login('presidente')
		page = self.client.get(reverse('eleisaun-live'))
		self.assertContains(page, 'id="komparaLabel"')
		self.assertContains(page, 'j.kpi.kompara.label')

