import datetime
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from config import roles
from custom.models import Municipality, AdministrativePost, Village, Aldeia, Organizasaun, Year
from membro.models import Membro, Alokasaun, Historia
from users.models import UserScope


class BaseCase(TestCase):
	@classmethod
	def setUpTestData(cls):
		for key, _ in roles.ROLE_LABELS:
			Group.objects.create(name=key)
		mun = Municipality.objects.create(name='Dili')
		post = AdministrativePost.objects.create(municipality=mun, name='Dom Aleixo')
		cls.va = Village.objects.create(administrativepost=post, name='Suku A')
		cls.vb = Village.objects.create(administrativepost=post, name='Suku B')
		cls.a1 = Aldeia.objects.create(village=cls.va, name='A1')
		cls.a2 = Aldeia.objects.create(village=cls.va, name='A2')
		cls.b1 = Aldeia.objects.create(village=cls.vb, name='B1')
		cls.org = Organizasaun.objects.create(code='OJD', name='OJD')
		cls.year = Year.objects.create(year=2026, is_active=True)
		cls.users = {}
		for name, role, scope in [
			('presidente', roles.PRESIDENTE, {}), ('koordpostu', roles.KOORD_POSTU, {}),
			('sekrpostu', roles.SEKR_POSTU, {}), ('admin', roles.ADMIN, {}),
			('koordsuku', roles.KOORD_SUKU, {'village': cls.va}),
			('sekrsuku', roles.SEKR_SUKU, {'village': cls.va}),
			('sekrsukub', roles.SEKR_SUKU, {'village': cls.vb}),
			('sekraldeia', roles.SEKR_ALDEIA, {'village': cls.va, 'aldeia': cls.a1}),
			('koordorg', roles.KOORD_ORG, {'organizasaun': cls.org}),
		]:
			u = User.objects.create_user(name, password='Teste-12345!')
			u.groups.add(Group.objects.get(name=role))
			UserScope.objects.create(user=u, **scope)
			cls.users[name] = u

	def login(self, name):
		self.client.logout()
		self.assertTrue(self.client.login(username=name, password='Teste-12345!'))

	def make(self, nu, village=None, aldeia=None, **kw):
		village = village or self.va
		aldeia = aldeia or (self.a1 if village == self.va else self.b1)
		data = dict(nome=f'Membru {nu}', sex='Mane', date_of_birth=datetime.date(1990, 1, 1),
			nu_eleitoral=nu, village=village, aldeia=aldeia, year=self.year, user=self.users['sekrsuku'])
		data.update(kw)
		return Membro.objects.create(**data)

	def form_data(self, nu='ABC1234', **kw):
		data = {'nome': 'Joao  Silva', 'sex': 'Mane', 'date_of_birth': '1990-05-04', 'nu_eleitoral': nu,
			'aldeia': self.a1.pk, 'status': 'Ativu'}
		data.update(kw)
		return data


class HashTests(BaseCase):
	def test_hashed_is_hmac_sha256(self):
		m = self.make('HASH001')
		self.assertEqual(len(m.hashed), 64)
		self.assertNotEqual(m.hashed, self.make('HASH002').hashed)


class ScopeTests(BaseCase):
	def setUp(self):
		self.ma1 = self.make('SCOPE01', self.va, self.a1)
		self.ma2 = self.make('SCOPE02', self.va, self.a2)
		self.mb1 = self.make('SCOPE03', self.vb, self.b1, organizasaun=self.org)

	def names(self, user):
		self.login(user)
		resp = self.client.get(reverse('membro-list'))
		self.assertEqual(resp.status_code, 200)
		return {o.nu_eleitoral for o in resp.context['objects']}

	def test_postu_roles_see_all(self):
		for u in ('presidente', 'koordpostu', 'sekrpostu'):
			self.assertEqual(self.names(u), {'SCOPE01', 'SCOPE02', 'SCOPE03'})

	def test_suku_sees_only_own_suku(self):
		self.assertEqual(self.names('koordsuku'), {'SCOPE01', 'SCOPE02'})

	def test_aldeia_sees_only_own_aldeia(self):
		self.assertEqual(self.names('sekraldeia'), {'SCOPE01'})

	def test_org_sees_only_own_org(self):
		self.assertEqual(self.names('koordorg'), {'SCOPE03'})

	def test_detail_outside_scope_is_404(self):
		self.login('sekraldeia')
		self.assertEqual(self.client.get(reverse('membro-detail', args=[self.ma2.hashed])).status_code, 404)
		self.assertEqual(self.client.get(reverse('membro-detail', args=[self.ma1.hashed])).status_code, 200)

	def test_admin_cannot_see_members(self):
		self.login('admin')
		self.assertEqual(self.client.get(reverse('membro-list')).status_code, 403)

	def test_anonymous_redirected_to_login(self):
		resp = self.client.get(reverse('membro-list'))
		self.assertEqual(resp.status_code, 302)
		self.assertIn('/login/', resp['Location'])


class InputTests(BaseCase):
	def test_only_secretaries_can_input(self):
		for u in ('presidente', 'koordpostu', 'koordsuku', 'admin', 'sekrpostu'):
			self.login(u)
			self.assertEqual(self.client.get(reverse('membro-add')).status_code, 403, u)
		for u in ('sekrsuku', 'sekraldeia'):
			self.login(u)
			self.assertEqual(self.client.get(reverse('membro-add')).status_code, 200, u)

	def test_create_sets_pending_year_and_history(self):
		self.login('sekrsuku')
		resp = self.client.post(reverse('membro-add'), self.form_data())
		self.assertEqual(resp.status_code, 302)
		m = Membro.objects.get(nu_eleitoral='ABC1234')
		self.assertEqual((m.aprovasaun, m.year, m.village, m.nome), ('Pendente', self.year, self.va, 'Joao Silva'))
		self.assertTrue(Historia.objects.filter(membro=m, aksaun='Kria').exists())

	def test_secretary_cannot_register_in_other_suku(self):
		self.login('sekrsuku')
		bad = self.form_data(nu='XYZ9999', aldeia=self.b1.pk, village=self.vb.pk)
		resp = self.client.post(reverse('membro-add'), bad)
		self.assertEqual(resp.status_code, 200)
		self.assertFalse(Membro.objects.filter(nu_eleitoral='XYZ9999').exists())

	def test_aldeia_secretary_forced_to_own_aldeia(self):
		self.login('sekraldeia')
		self.client.post(reverse('membro-add'), self.form_data(nu='ALD0001', aldeia=self.a2.pk))
		self.assertFalse(Membro.objects.filter(nu_eleitoral='ALD0001', aldeia=self.a2).exists())

	def test_duplicate_nu_eleitoral_is_blocked_with_notice(self):
		self.make('DUP0001', self.vb, self.b1)
		self.login('sekrsuku')
		resp = self.client.post(reverse('membro-add'), self.form_data(nu='dup0001'))
		self.assertEqual(resp.status_code, 200)
		self.assertContains(resp, 'DUPLIKADU')
		self.assertEqual(Membro.objects.filter(nu_eleitoral__iexact='DUP0001').count(), 1)

	def test_no_active_year_blocks_input(self):
		Year.objects.update(is_active=False)
		self.login('sekrsuku')
		resp = self.client.get(reverse('membro-add'))
		self.assertRedirects(resp, reverse('membro-list'))


class ApprovalTests(BaseCase):
	def setUp(self):
		self.m = self.make('APR0001')

	def test_only_postu_leaders_approve(self):
		for u in ('koordsuku', 'sekrsuku', 'sekrpostu', 'admin'):
			self.login(u)
			resp = self.client.post(reverse('aprovasaun-aprova', args=[self.m.hashed]))
			self.assertEqual(resp.status_code, 403, u)
		self.m.refresh_from_db()
		self.assertEqual(self.m.aprovasaun, 'Pendente')

	def test_both_presidente_and_koord_postu_can_approve(self):
		for u in ('presidente', 'koordpostu'):
			m = self.make(f'APR-{u}')
			self.login(u)
			self.client.post(reverse('aprovasaun-aprova', args=[m.hashed]))
			m.refresh_from_db()
			self.assertEqual((m.aprovasaun, m.aprovadu_husi.username), ('Aprovadu', u))

	def test_approve_requires_post(self):
		self.login('presidente')
		self.assertEqual(self.client.get(reverse('aprovasaun-aprova', args=[self.m.hashed])).status_code, 405)

	def test_reject_requires_reason(self):
		self.login('koordpostu')
		url = reverse('aprovasaun-rejeita', args=[self.m.hashed])
		self.assertEqual(self.client.post(url, {'razaun': ''}).status_code, 200)
		self.m.refresh_from_db()
		self.assertEqual(self.m.aprovasaun, 'Pendente')
		self.client.post(url, {'razaun': 'Nu. eleitoral la loos'})
		self.m.refresh_from_db()
		self.assertEqual((self.m.aprovasaun, self.m.razaun_rejeita), ('Rejeitadu', 'Nu. eleitoral la loos'))

	def test_bulk_approve_respects_scope_and_state(self):
		other = self.make('APR0002', self.vb, self.b1)
		self.login('presidente')
		self.client.post(reverse('aprovasaun-bulk'), {'hashid': [self.m.hashed, other.hashed]})
		self.assertEqual(Membro.objects.filter(aprovasaun='Aprovadu').count(), 2)

	def test_edit_after_approval_goes_back_to_pending(self):
		self.login('presidente')
		self.client.post(reverse('aprovasaun-aprova', args=[self.m.hashed]))
		self.login('sekrsuku')
		data = self.form_data(nu='APR0001', nome='Nome Foun')
		self.client.post(reverse('membro-update', args=[self.m.hashed]), data)
		self.m.refresh_from_db()
		self.assertEqual((self.m.nome, self.m.aprovasaun, self.m.aprovadu_husi), ('Nome Foun', 'Pendente', None))
		edit = Historia.objects.filter(membro=self.m, aksaun='Edita').first()
		self.assertIn('Naran', edit.detalhe)

	def test_secretary_cannot_edit_outside_scope(self):
		self.login('sekrsukub')
		self.assertEqual(self.client.get(reverse('membro-update', args=[self.m.hashed])).status_code, 404)

	def test_delete_logged_and_post_only(self):
		self.login('presidente')
		url = reverse('membro-del', args=[self.m.hashed])
		self.assertEqual(self.client.get(url).status_code, 405)
		self.client.post(url)
		self.assertFalse(Membro.objects.filter(pk=self.m.pk).exists())
		self.assertTrue(Historia.objects.filter(aksaun='Hamoos', membro__isnull=True).exists())


class AlokasaunTests(BaseCase):
	def setUp(self):
		self.m1 = self.make('ALO0001', aprovasaun='Aprovadu')
		self.m2 = self.make('ALO0002', aprovasaun='Aprovadu')

	def data(self, membro, **kw):
		d = {'membro': membro.pk, 'nivel': 'Suku', 'pozisaun': 'Coordenador', 'village': self.va.pk,
			'data_hahu': '2026-01-01', 'ativu': 'Sim'}
		d.update(kw)
		return d

	def test_only_presidente_allocates(self):
		for u in ('koordpostu', 'sekrsuku', 'koordsuku'):
			self.login(u)
			self.assertEqual(self.client.get(reverse('alokasaun-add')).status_code, 403, u)
		self.login('presidente')
		resp = self.client.post(reverse('alokasaun-add'), self.data(self.m1))
		self.assertRedirects(resp, reverse('alokasaun-list'))
		self.assertTrue(Alokasaun.objects.filter(membro=self.m1, pozisaun='Coordenador').exists())

	def test_only_one_active_coordenador_per_unit(self):
		self.login('presidente')
		self.client.post(reverse('alokasaun-add'), self.data(self.m1))
		resp = self.client.post(reverse('alokasaun-add'), self.data(self.m2))
		self.assertEqual(resp.status_code, 200)
		self.assertContains(resp, 'ativu iha ona')
		self.assertEqual(Alokasaun.objects.count(), 1)

	def test_member_must_belong_to_unit(self):
		other = self.make('ALO0003', self.vb, self.b1, aprovasaun='Aprovadu')
		self.login('presidente')
		resp = self.client.post(reverse('alokasaun-add'), self.data(other))
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(Alokasaun.objects.count(), 0)

	def test_only_approved_members_selectable(self):
		pend = self.make('ALO0004')
		self.login('presidente')
		resp = self.client.post(reverse('alokasaun-add'), self.data(pend))
		self.assertEqual(Alokasaun.objects.count(), 0)
		self.assertEqual(resp.status_code, 200)

	def test_presidente_only_at_postu_level(self):
		self.login('presidente')
		resp = self.client.post(reverse('alokasaun-add'), self.data(self.m1, pozisaun='Presidente'))
		self.assertEqual(Alokasaun.objects.count(), 0)
		resp = self.client.post(reverse('alokasaun-add'), {
			'membro': self.m1.pk, 'nivel': 'Postu', 'pozisaun': 'Presidente', 'data_hahu': '2026-01-01', 'ativu': 'Sim'})
		self.assertEqual(Alokasaun.objects.count(), 1)

	def test_organization_level(self):
		m = self.make('ALO0005', aprovasaun='Aprovadu', organizasaun=self.org)
		self.login('presidente')
		self.client.post(reverse('alokasaun-add'), {
			'membro': m.pk, 'nivel': 'Organizasaun', 'pozisaun': 'Sekretariu', 'organizasaun': self.org.pk,
			'data_hahu': '2026-01-01', 'ativu': 'Sim'})
		self.assertEqual(Alokasaun.objects.get().organizasaun, self.org)

	def test_suku_user_sees_only_own_structure(self):
		Alokasaun.objects.create(membro=self.m1, nivel='Suku', pozisaun='Coordenador', village=self.va, data_hahu=datetime.date(2026, 1, 1))
		ob = self.make('ALO0006', self.vb, self.b1, aprovasaun='Aprovadu')
		Alokasaun.objects.create(membro=ob, nivel='Suku', pozisaun='Coordenador', village=self.vb, data_hahu=datetime.date(2026, 1, 1))
		self.login('koordsuku')
		resp = self.client.get(reverse('alokasaun-list'))
		self.assertEqual([a.membro for a in resp.context['objects']], [self.m1])


class HistoriaAndApiTests(BaseCase):
	def test_history_access(self):
		self.make('HIS0001')
		for u, code in [('admin', 200), ('presidente', 200), ('koordpostu', 200),
				('sekrpostu', 403), ('sekrsuku', 403), ('koordsuku', 403)]:
			self.login(u)
			self.assertEqual(self.client.get(reverse('historia-list')).status_code, code, u)

	def test_api_is_scoped(self):
		self.make('API0001', self.va, self.a1)
		self.make('API0002', self.vb, self.b1)
		self.login('koordsuku')
		data = self.client.get(reverse('api-suku')).json()
		self.assertEqual((data['label'], data['obj']), (['Suku A'], [1]))
		self.login('presidente')
		data = self.client.get(reverse('api-suku')).json()
		self.assertEqual(data['obj'], [1, 1])

	def test_api_requires_login_and_role(self):
		self.client.logout()
		self.assertIn(self.client.get(reverse('api-gender')).status_code, (401, 403))
		self.login('admin')
		self.assertEqual(self.client.get(reverse('api-gender')).status_code, 403)

	def test_dashboard_renders(self):
		self.make('DASH001', organizasaun=self.org)
		self.login('presidente')
		resp = self.client.get(reverse('report-dash'))
		self.assertEqual(resp.status_code, 200)
		self.assertContains(resp, 'Suku A')


class UserAdminTests(BaseCase):
	def user_data(self, **kw):
		d = {'username': 'novu', 'first_name': 'Novu', 'email': '', 'is_active': 'on',
			'group': roles.SEKR_SUKU, 'village': self.va.pk, 'password': 'Aman-Sekali-2026'}
		d.update(kw)
		return d

	def test_only_admin_manages_users(self):
		for u in ('presidente', 'koordpostu', 'sekrsuku'):
			self.login(u)
			self.assertEqual(self.client.get(reverse('user-list')).status_code, 403, u)
		self.login('admin')
		self.assertEqual(self.client.get(reverse('user-list')).status_code, 200)

	def test_create_user_with_scope(self):
		self.login('admin')
		resp = self.client.post(reverse('user-add'), self.user_data())
		self.assertRedirects(resp, reverse('user-list'))
		u = User.objects.get(username='novu')
		self.assertTrue(u.check_password('Aman-Sekali-2026'))
		self.assertEqual((u.groups.get().name, u.scope.village), (roles.SEKR_SUKU, self.va))

	def test_suku_role_requires_suku(self):
		self.login('admin')
		self.client.post(reverse('user-add'), self.user_data(village=''))
		self.assertFalse(User.objects.filter(username='novu').exists())

	def test_weak_password_rejected(self):
		self.login('admin')
		self.client.post(reverse('user-add'), self.user_data(password='12345678'))
		self.assertFalse(User.objects.filter(username='novu').exists())

	def test_admin_cannot_deactivate_self(self):
		self.login('admin')
		me = self.users['admin']
		data = self.user_data(username='admin', group=roles.ADMIN, village='', password='')
		data.pop('is_active')
		self.client.post(reverse('user-update', args=[me.pk]), data)
		me.refresh_from_db()
		self.assertTrue(me.is_active)

	def test_master_data_only_admin(self):
		self.login('presidente')
		self.assertEqual(self.client.get(reverse('master-list', args=['suku'])).status_code, 403)
		self.login('admin')
		resp = self.client.post(reverse('master-add', args=['suku']), {'name': 'Suku C'})
		self.assertEqual(resp.status_code, 302)
		self.assertTrue(Village.objects.filter(name='Suku C', administrativepost__name='Dom Aleixo').exists())

	def test_only_one_active_year(self):
		self.login('admin')
		y = Year.objects.create(year=2027)
		self.client.post(reverse('ano-aktiva', args=[y.pk]))
		self.assertEqual(list(Year.objects.filter(is_active=True)), [y])

	def test_cannot_delete_used_master(self):
		self.make('USE0001')
		self.login('admin')
		self.client.post(reverse('master-del', args=['suku', self.va.pk]))
		self.assertTrue(Village.objects.filter(pk=self.va.pk).exists())


class LayoutAndReportTests(BaseCase):
	def menu(self, user, url='/'):
		self.login(user)
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)
		return [i['label'] for i in resp.context['nav_items']]

	def test_menu_per_role(self):
		self.assertEqual(self.menu('admin'), ['Varanda', 'Uzuáriu', 'Data Master', 'Historia'])
		self.assertEqual(self.menu('presidente'),
			['Varanda', 'Dashboard', 'Grafik', 'Membru', 'Aprovasaun', 'Struktura', 'Historia'])
		self.assertEqual(self.menu('sekrsuku'), ['Varanda', 'Dashboard', 'Grafik', 'Membru', 'Aumenta', 'Struktura'])
		self.assertEqual(self.menu('koordsuku'), ['Varanda', 'Dashboard', 'Grafik', 'Membru', 'Struktura'])

	def test_active_menu_item(self):
		self.login('presidente')
		resp = self.client.get(reverse('report-chart'))
		active = [i['label'] for i in resp.context['nav_items'] if i['active']]
		self.assertEqual(active, ['Grafik'])

	def test_navbar_has_sidebar_and_logout_form(self):
		self.login('presidente')
		resp = self.client.get('/')
		self.assertContains(resp, 'id="sidebar"')
		self.assertContains(resp, 'id="btn-ham"')
		self.assertContains(resp, 'action="/logout/"')

	def test_login_page_has_no_menu(self):
		self.client.logout()
		resp = self.client.get(reverse('login'))
		self.assertNotContains(resp, 'id="sidebar"')

	def test_chart_page_and_extra_apis(self):
		self.make('CH00001', aprovasaun='Aprovadu')
		self.login('presidente')
		self.assertEqual(self.client.get(reverse('report-chart')).status_code, 200)
		self.assertEqual(self.client.get(reverse('api-aldeia')).json()['obj'], [1])
		self.assertEqual(self.client.get(reverse('api-status')).json()['label'], ['Ativu'])
		self.login('admin')
		self.assertEqual(self.client.get(reverse('report-chart')).status_code, 403)

	def test_dashboard_numbers_are_scoped(self):
		self.make('DB00001', self.va, self.a1, sex='Mane')
		self.make('DB00002', self.vb, self.b1, sex='Feto', aprovasaun='Aprovadu')
		self.login('koordsuku')
		tot = self.client.get(reverse('report-dash')).context['tot']
		self.assertEqual((tot['total'], tot['mane'], tot['feto'], tot['pendente']), (1, 1, 0, 1))
		self.login('presidente')
		tot = self.client.get(reverse('report-dash')).context['tot']
		self.assertEqual((tot['total'], tot['aprovadu']), (2, 1))

	def test_list_filters_from_dashboard_links(self):
		self.make('FL00001', sex='Mane', data_hakbit=datetime.date(2015, 5, 1))
		self.make('FL00002', sex='Feto', data_hakbit=datetime.date(2020, 5, 1))
		self.login('presidente')
		get = lambda q: {o.nu_eleitoral for o in self.client.get(reverse('membro-list') + q).context['objects']}
		self.assertEqual(get('?sex=Feto'), {'FL00002'})
		self.assertEqual(get('?hakbit=2015'), {'FL00001'})
		self.assertEqual(get('?hakbit=abc'), {'FL00001', 'FL00002'})
		self.assertEqual(get('?village=abc'), {'FL00001', 'FL00002'})
