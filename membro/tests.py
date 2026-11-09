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
			('sekrorg', roles.SEKR_ORG, {'organizasaun': cls.org}),
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
		for u in ('sekrsuku', 'sekraldeia', 'sekrorg'):
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
			['Varanda', 'Relatoriu', 'Membru', 'Aprovasaun', 'Struktura', 'Historia'])
		self.assertEqual(self.menu('sekrsuku'), ['Varanda', 'Relatoriu', 'Membru', 'Aumenta', 'Struktura'])
		self.assertEqual(self.menu('sekrorg'), ['Varanda', 'Relatoriu', 'Membru', 'Aumenta', 'Struktura'])
		self.assertEqual(self.menu('koordsuku'), ['Varanda', 'Relatoriu', 'Membru', 'Struktura'])

	def test_active_menu_item(self):
		self.login('presidente')
		resp = self.client.get(reverse('report-chart'))
		active = [i['label'] for i in resp.context['nav_items'] if i['active']]
		self.assertEqual(active, ['Relatoriu'])
		rel = [i for i in resp.context['nav_items'] if i['label'] == 'Relatoriu'][0]
		self.assertEqual([(c['label'], c['active']) for c in rel['children']], [('Tabular', False), ('Grafiku', True)])

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


class HomeAndExtraApiTests(BaseCase):
	def test_age_marital_hakbit_apis(self):
		today = datetime.date.today()
		self.make('X0000001', date_of_birth=today.replace(year=today.year - 20), marital='Casado/a',
			data_hakbit=datetime.date(2018, 1, 1))
		self.make('X0000002', date_of_birth=today.replace(year=today.year - 70))
		self.make('X0000003', self.vb, self.b1, date_of_birth=today.replace(year=today.year - 20))
		self.login('koordsuku')
		age = self.client.get(reverse('api-age')).json()
		self.assertEqual(dict(zip(age['label'], age['obj'])), {'< 18': 0, '18-25': 1, '26-35': 0, '36-45': 0,
			'46-55': 0, '56-65': 0, '> 65': 1})
		self.assertEqual(self.client.get(reverse('api-hakbit')).json(), {'label': ['2018'], 'obj': [1]})
		self.assertEqual(sorted(self.client.get(reverse('api-marital')).json()['label']), ['Casado/a', 'Laiha'])
		self.login('presidente')
		self.assertEqual(sum(self.client.get(reverse('api-age')).json()['obj']), 3)
		self.login('admin')
		self.assertEqual(self.client.get(reverse('api-age')).status_code, 403)

	def test_topbar_has_short_mobile_text(self):
		self.login('presidente')
		resp = self.client.get('/')
		self.assertContains(resp, 'd-sm-none">Dom Aleixo</span>')


class NotificationTests(BaseCase):
	def badge(self, user):
		self.login(user)
		resp = self.client.get(reverse('api-notif-badge'))
		self.assertEqual(resp.status_code, 200)
		return resp.json()

	def test_requires_login(self):
		self.client.logout()
		self.assertIn(self.client.get(reverse('api-notif-badge')).status_code, (401, 403))

	def test_approver_counts_pending(self):
		self.make('NT00001'); self.make('NT00002', self.vb, self.b1)
		self.make('NT00003', aprovasaun='Aprovadu'); self.make('NT00004', aprovasaun='Rejeitadu')
		for u in ('presidente', 'koordpostu'):
			self.assertEqual(self.badge(u), {'value': 2, 'pendente': 2, 'rejeitadu': 0}, u)
		self.assertEqual(self.client.get(reverse('api-notif-pendente')).json(), {'value': 2})

	def test_secretary_counts_rejected_in_own_scope_only(self):
		self.make('NT00005', aprovasaun='Rejeitadu')
		self.make('NT00006', self.vb, self.b1, aprovasaun='Rejeitadu')
		self.make('NT00007')
		self.assertEqual(self.badge('sekrsuku'), {'value': 1, 'pendente': 0, 'rejeitadu': 1})
		self.assertEqual(self.client.get(reverse('api-notif-rejeitadu')).json(), {'value': 1})
		self.assertEqual(self.badge('sekrsukub')['rejeitadu'], 1)

	def test_other_roles_get_zero(self):
		self.make('NT00008'); self.make('NT00009', aprovasaun='Rejeitadu')
		for u in ('koordsuku', 'sekrpostu', 'koordorg', 'admin'):
			self.assertEqual(self.badge(u)['value'], 0, u)

	def test_bell_rendered_only_for_roles_with_notifications(self):
		self.make('NT00010')
		self.login('presidente')
		resp = self.client.get('/')
		self.assertContains(resp, 'id="notifDropdown"')
		self.assertContains(resp, 'data-url="/api/notification/badge/"')
		self.assertContains(resp, 'id="notifbadge"')
		self.assertContains(resp, 'notification.js')
		self.assertEqual([i['key'] for i in resp.context['notif_items']], ['pendente'])
		self.login('sekrsuku')
		self.assertEqual([i['key'] for i in self.client.get('/').context['notif_items']], ['rejeitadu'])
		self.login('koordsuku')
		self.assertNotContains(self.client.get('/'), 'id="notifDropdown"')
		self.login('admin')
		self.assertNotContains(self.client.get('/'), 'id="notifDropdown"')

	def test_initial_badge_has_count_without_waiting_for_polling(self):
		self.make('NT00011'); self.make('NT00012')
		self.login('presidente')
		self.assertContains(self.client.get('/'), '<span id="notifbadge" class="badge badge-danger">2</span>')


class StrukturaDashTests(BaseCase):
	def setUp(self):
		self.m1 = self.make('ST00001', self.va, self.a1, aprovasaun='Aprovadu')
		self.m2 = self.make('ST00002', self.va, self.a1, aprovasaun='Aprovadu')
		self.mb = self.make('ST00003', self.vb, self.b1, aprovasaun='Aprovadu')
		d = datetime.date(2026, 1, 1)
		Alokasaun.objects.create(membro=self.m1, nivel='Suku', pozisaun='Coordenador', village=self.va, data_hahu=d)
		Alokasaun.objects.create(membro=self.m2, nivel='Aldeia', pozisaun='Coordenador', aldeia=self.a1, data_hahu=d)
		Alokasaun.objects.create(membro=self.mb, nivel='Suku', pozisaun='Sekretariu', village=self.vb, data_hahu=d)
		Alokasaun.objects.create(membro=self.m1, nivel='Postu', pozisaun='Presidente', data_hahu=d)

	def dash(self, user):
		self.login(user)
		resp = self.client.get(reverse('alokasaun-dash'))
		self.assertEqual(resp.status_code, 200)
		return resp

	def test_presidente_sees_full_matrix_with_coverage(self):
		resp = self.dash('presidente')
		rows = {r['v'].name: r for r in resp.context['rows_suku']}
		self.assertEqual((rows['Suku A']['a_total'], rows['Suku A']['a_coord'], rows['Suku A']['a_sekr']), (2, 1, 0))
		self.assertEqual(rows['Suku A']['coord'].membro, self.m1)
		self.assertIsNone(rows['Suku A']['sekr'])
		self.assertEqual(rows['Suku B']['sekr'].membro, self.mb)
		self.assertEqual(dict(resp.context['postu'])['Presidente'].membro, self.m1)
		self.assertContains(resp, 'Aloka Pozisaun')
		self.assertContains(resp, 'Lista Jeral Pozisaun')
		self.assertContains(resp, 'chart_alokasaun')

	def test_suku_user_sees_only_own_suku_and_no_postu_table(self):
		resp = self.dash('koordsuku')
		self.assertEqual([r['v'].name for r in resp.context['rows_suku']], ['Suku A'])
		self.assertEqual({r['a'].name for r in resp.context['rows_aldeia']}, {'A1', 'A2'})
		self.assertFalse(resp.context['show_postu'])
		self.assertNotContains(resp, 'Aloka Pozisaun')

	def test_aldeia_user_scope(self):
		resp = self.dash('sekraldeia')
		self.assertEqual([r['a'].name for r in resp.context['rows_aldeia']], ['A1'])
		self.assertEqual([r['v'].name for r in resp.context['rows_suku']], ['Suku A'])

	def test_org_user_sees_only_own_org(self):
		resp = self.dash('koordorg')
		self.assertEqual([r['o'].code for r in resp.context['rows_org']], ['OJD'])
		self.assertEqual(resp.context['rows_suku'], [])

	def test_admin_forbidden(self):
		self.login('admin')
		self.assertEqual(self.client.get(reverse('alokasaun-dash')).status_code, 403)

	def test_inactive_allocation_not_counted(self):
		Alokasaun.objects.filter(pozisaun='Presidente').update(ativu='Lae')
		self.assertIsNone(dict(self.dash('presidente').context['postu'])['Presidente'])

	def test_list_filters_from_dash_links(self):
		self.login('presidente')
		get = lambda q: [(a.nivel, a.pozisaun) for a in self.client.get(reverse('alokasaun-list') + q).context['objects']]
		self.assertEqual(get('?nivel=Suku&pozisaun=Coordenador&village=%d' % self.va.pk), [('Suku', 'Coordenador')])
		self.assertEqual(get('?nivel=Aldeia&pozisaun=Coordenador&village=%d' % self.va.pk), [('Aldeia', 'Coordenador')])
		self.assertEqual(get('?nivel=Aldeia&village=%d' % self.vb.pk), [])
		self.assertEqual(len(get('?nivel=abc&village=xyz')), 4)

	def test_scoped_list_filter_cannot_widen_scope(self):
		self.login('koordsuku')
		objs = self.client.get(reverse('alokasaun-list') + '?village=%d' % self.vb.pk).context['objects']
		self.assertEqual(list(objs), [])

	def test_menu_struktura_points_to_dash(self):
		self.login('presidente')
		resp = self.client.get(reverse('alokasaun-dash'))
		struktura = [i for i in resp.context['nav_items'] if i['label'] == 'Struktura'][0]
		self.assertEqual(struktura['url'], reverse('alokasaun-dash'))
		self.assertTrue(struktura['active'])

	def test_alokasaun_api_scoped(self):
		self.login('presidente')
		data = self.client.get(reverse('api-alokasaun')).json()
		self.assertEqual(dict(zip(data['label'], data['obj'])),
			{'Postu · Presidente': 1, 'Suku · Coordenador': 1, 'Suku · Sekretariu': 1, 'Aldeia · Coordenador': 1})
		self.login('koordsuku')
		data = self.client.get(reverse('api-alokasaun')).json()
		self.assertEqual(sum(data['obj']), 2)


class RekapButtonsTests(BaseCase):
	def test_buttons_per_role(self):
		self.make('RK00001')
		self.login('sekrsuku')
		resp = self.client.get(reverse('report-dash'))
		self.assertContains(resp, 'Aumenta Membru')
		self.assertContains(resp, 'Lista Jeral Membru')
		self.assertContains(resp, 'Grafiku')
		self.assertNotContains(resp, 'href="/membro/aprovasaun/"')
		self.login('presidente')
		resp = self.client.get(reverse('report-dash'))
		self.assertContains(resp, 'Hein Aprovasaun (1)')
		self.assertNotContains(resp, 'Aumenta Membru')
		self.assertContains(resp, 'TINAN 2026')


# ---------------------------------------------------------------- upload foto / PDF eleitoral
import io
import re
import shutil
import tempfile
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from unittest import mock
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, TextStringObject

PRIVATE_TMP = tempfile.mkdtemp(prefix='pdpada-private-')


def img_bytes(fmt='PNG', size=(40, 30), mode='RGB', color=(10, 80, 200), trailer=b'', exif_make=None):
	buf = io.BytesIO()
	img = Image.new(mode, size, color if mode in ('RGB', 'RGBA') else 128)
	kw = {}
	if exif_make:
		ex = Image.Exif()
		ex[0x010F] = exif_make  # tag Make
		kw['exif'] = ex.tobytes()
	img.save(buf, fmt, **kw)
	return buf.getvalue() + trailer


def pdf_bytes(pages=1, js=False, encrypt=False):
	w = PdfWriter()
	for _ in range(pages):
		w.add_blank_page(72, 72)
	if js:  # OpenAction JavaScript di root dokumen
		action = DictionaryObject({NameObject('/S'): NameObject('/JavaScript'), NameObject('/JS'): TextStringObject("app.alert('x')")})
		w._root_object[NameObject('/OpenAction')] = w._add_object(action)
	if encrypt:
		w.encrypt('rahasia', algorithm='RC4-128')
	buf = io.BytesIO()
	w.write(buf)
	return buf.getvalue()


@override_settings(PRIVATE_ROOT=PRIVATE_TMP)
class UploadBase(BaseCase):
	@classmethod
	def tearDownClass(cls):
		super().tearDownClass()
		shutil.rmtree(PRIVATE_TMP, ignore_errors=True)

	def post_member(self, nu='UP00001', image=None, pdf=None, **kw):
		self.login('sekrsuku')
		data = self.form_data(nu=nu, **kw)
		if image is not None:
			data['image'] = image
		if pdf is not None:
			data['file_eleitoral'] = pdf
		return self.client.post(reverse('membro-add'), data)

	def jpg(self, name='foto.jpg', **kw):
		return SimpleUploadedFile(name, img_bytes('JPEG', **kw), content_type='image/jpeg')

	def pdf(self, name='kartaun.pdf', **kw):
		return SimpleUploadedFile(name, pdf_bytes(**kw), content_type='application/pdf')


class NuBiRemovedTests(BaseCase):
	def test_nu_bi_field_is_gone(self):
		from membro.forms import MembroForm
		self.assertNotIn('nu_bi', [f.name for f in Membro._meta.get_fields()])
		self.assertNotIn('nu_bi', MembroForm(user=self.users['sekrsuku']).fields)
		self.make('BI00001')
		self.login('presidente')
		m = Membro.objects.get(nu_eleitoral='BI00001')
		self.assertNotContains(self.client.get(reverse('membro-detail', args=[m.hashed])), 'Nu. BI')


class PhotoUploadTests(UploadBase):
	def test_valid_photo_is_reencoded_and_renamed_with_new_hash(self):
		resp = self.post_member(image=SimpleUploadedFile('Foto Asli Saya.PNG', img_bytes('PNG', mode='RGBA'), content_type='image/png'))
		self.assertEqual(resp.status_code, 302)
		m = Membro.objects.get(nu_eleitoral='UP00001')
		self.assertRegex(m.image.name, r'^foto/[0-9a-f]{64}\.jpg$')
		self.assertNotIn('asli', m.image.name.lower())
		with Image.open(m.image.path) as stored:
			self.assertEqual(stored.format, 'JPEG')

	def test_same_file_gets_different_name_each_time(self):
		self.post_member(nu='UP00002', image=self.jpg())
		self.post_member(nu='UP00003', image=self.jpg())
		a = Membro.objects.get(nu_eleitoral='UP00002').image.name
		b = Membro.objects.get(nu_eleitoral='UP00003').image.name
		self.assertNotEqual(a, b)

	def test_exif_metadata_is_stripped(self):
		self.post_member(image=self.jpg(exif_make='SPIONASE'))
		m = Membro.objects.get(nu_eleitoral='UP00001')
		with Image.open(m.image.path) as stored:
			self.assertEqual(len(stored.getexif()), 0)
		self.assertNotIn(b'SPIONASE', open(m.image.path, 'rb').read())

	def test_appended_payload_is_removed(self):
		payload = b'<?php system($_GET["c"]); ?>PK\x03\x04'
		up = SimpleUploadedFile('x.jpg', img_bytes('JPEG', trailer=payload), content_type='image/jpeg')
		self.post_member(image=up)
		m = Membro.objects.get(nu_eleitoral='UP00001')
		data = open(m.image.path, 'rb').read()
		self.assertNotIn(b'<?php', data)
		self.assertNotIn(b'PK\x03\x04', data)

	def test_error_message_is_in_tetun(self):
		resp = self.post_member(image=SimpleUploadedFile('foto.jpg', b'bukan gambar', content_type='image/jpeg'))
		self.assertContains(resp, "Fotu la válidu")
		self.assertNotContains(resp, 'Upload a valid image')

	def test_fake_image_with_jpg_extension_is_rejected(self):
		for content in (b'ini hanya teks biasa', b'<html><script>alert(1)</script></html>', b'%PDF-1.4 palsu', b'\xff\xd8\xff palsu'):
			resp = self.post_member(image=SimpleUploadedFile('foto.jpg', content, content_type='image/jpeg'))
			self.assertEqual(resp.status_code, 200)
			self.assertFalse(Membro.objects.filter(nu_eleitoral='UP00001').exists())

	def test_gif_and_webp_formats_are_rejected(self):
		for fmt in ('GIF', 'WEBP'):
			up = SimpleUploadedFile('foto.jpg', img_bytes(fmt), content_type='image/jpeg')
			self.post_member(image=up)
			self.assertFalse(Membro.objects.filter(nu_eleitoral='UP00001').exists(), fmt)

	def test_oversize_photo_is_rejected(self):
		big = SimpleUploadedFile('besar.jpg', img_bytes('JPEG') + b'\0' * (2 * 1024 * 1024 + 10), content_type='image/jpeg')
		self.post_member(image=big)
		self.assertFalse(Membro.objects.filter(nu_eleitoral='UP00001').exists())

	def test_too_many_pixels_is_rejected(self):
		up = SimpleUploadedFile('raksasa.png', img_bytes('PNG', size=(5100, 5100), mode='L'), content_type='image/png')
		self.post_member(image=up)
		self.assertFalse(Membro.objects.filter(nu_eleitoral='UP00001').exists())

	def test_large_photo_is_scaled_down(self):
		up = SimpleUploadedFile('lebar.png', img_bytes('PNG', size=(3000, 1500)), content_type='image/png')
		self.post_member(image=up)
		with Image.open(Membro.objects.get(nu_eleitoral='UP00001').image.path) as stored:
			self.assertEqual(max(stored.size), 1600)


class EleitoralPdfTests(UploadBase):
	def test_valid_pdf_is_stored_with_hashed_name(self):
		resp = self.post_member(pdf=self.pdf(name='KARTAUN ELEITORAL SAYA.pdf'))
		self.assertEqual(resp.status_code, 302)
		m = Membro.objects.get(nu_eleitoral='UP00001')
		self.assertRegex(m.file_eleitoral.name, r'^eleitoral/[0-9a-f]{64}\.pdf$')
		self.assertTrue(open(m.file_eleitoral.path, 'rb').read().startswith(b'%PDF-'))

	def rejected(self, upload):
		resp = self.post_member(pdf=upload)
		self.assertEqual(resp.status_code, 200)
		self.assertFalse(Membro.objects.filter(nu_eleitoral='UP00001').exists())

	def test_fake_pdf_is_rejected(self):
		self.rejected(SimpleUploadedFile('a.pdf', b'bukan pdf sama sekali', content_type='application/pdf'))
		self.rejected(SimpleUploadedFile('a.pdf', b'%PDF-1.4\nisi ngawur tanpa struktur', content_type='application/pdf'))
		self.rejected(SimpleUploadedFile('a.pdf', img_bytes('PNG'), content_type='application/pdf'))
		self.rejected(SimpleUploadedFile('a.pdf', pdf_bytes()[:-30], content_type='application/pdf'))  # terpotong

	def test_pdf_with_javascript_is_rejected(self):
		self.rejected(SimpleUploadedFile('a.pdf', pdf_bytes(js=True), content_type='application/pdf'))

	def test_pdf_with_launch_or_embedded_file_is_rejected(self):
		evil = pdf_bytes().replace(b'%%EOF', b'/Type /Action /S /Launch /F (cmd.exe)\n%%EOF')
		self.rejected(SimpleUploadedFile('a.pdf', evil, content_type='application/pdf'))
		evil2 = pdf_bytes().replace(b'%%EOF', b'/EmbeddedFile\n%%EOF')
		self.rejected(SimpleUploadedFile('a.pdf', evil2, content_type='application/pdf'))

	def test_structural_check_catches_javascript_even_if_raw_scan_is_bypassed(self):
		from config.file_utils import validate_pdf_content
		from django.core.exceptions import ValidationError
		up = SimpleUploadedFile('a.pdf', pdf_bytes(js=True), content_type='application/pdf')
		with mock.patch('config.file_utils.PDF_DANGEROUS') as fake:  # simulasi nama PDF yang disamarkan (#4A...)
			fake.search.return_value = None
			with self.assertRaises(ValidationError):
				validate_pdf_content(up)

	def test_clean_pdf_passes_validator(self):
		from config.file_utils import validate_pdf_content
		validate_pdf_content(SimpleUploadedFile('a.pdf', pdf_bytes(pages=2), content_type='application/pdf'))

	def test_encrypted_pdf_is_rejected(self):
		try:
			data = pdf_bytes(encrypt=True)
		except Exception:
			self.skipTest('enkripsi PDF tidak tersedia')
		self.rejected(SimpleUploadedFile('a.pdf', data, content_type='application/pdf'))

	def test_too_many_pages_is_rejected(self):
		self.rejected(SimpleUploadedFile('a.pdf', pdf_bytes(pages=21), content_type='application/pdf'))

	def test_oversize_pdf_is_rejected(self):
		self.rejected(SimpleUploadedFile('a.pdf', pdf_bytes() + b'\0' * (5 * 1024 * 1024 + 10), content_type='application/pdf'))

	def test_image_as_eleitoral_is_rejected(self):
		self.rejected(SimpleUploadedFile('a.pdf', img_bytes('JPEG'), content_type='application/pdf'))


class PrivateFileServingTests(UploadBase):
	def setUp(self):
		self.post_member(image=self.jpg(), pdf=self.pdf())
		self.m = Membro.objects.get(nu_eleitoral='UP00001')

	def url(self, kind, m=None):
		return reverse('membro-file', args=[(m or self.m).hashed, kind])

	def test_files_live_outside_media_and_have_no_public_url(self):
		self.assertTrue(self.m.image.path.startswith(PRIVATE_TMP))
		self.assertFalse(self.m.image.path.startswith(str(settings.MEDIA_ROOT)))
		with self.assertRaises(ValueError):
			self.m.image.url
		with self.assertRaises(ValueError):
			self.m.file_eleitoral.url

	def test_authorised_user_gets_photo_and_pdf_with_safe_headers(self):
		self.login('presidente')
		foto = self.client.get(self.url('foto'))
		self.assertEqual((foto.status_code, foto['Content-Type']), (200, 'image/jpeg'))
		self.assertEqual(foto['X-Content-Type-Options'], 'nosniff')
		self.assertIn('no-store', foto['Cache-Control'])
		self.assertTrue(b''.join(foto.streaming_content).startswith(b'\xff\xd8'))
		pdf = self.client.get(self.url('eleitoral'))
		self.assertEqual((pdf.status_code, pdf['Content-Type']), (200, 'application/pdf'))
		self.assertNotIn(self.m.file_eleitoral.name.split('/')[-1], pdf['Content-Disposition'])
		self.assertTrue(b''.join(pdf.streaming_content).startswith(b'%PDF-'))

	def test_pdf_view_is_audited_in_historia(self):
		self.login('presidente')
		self.client.get(self.url('eleitoral'))
		self.assertTrue(Historia.objects.filter(membro=self.m, aksaun='Hare Dokumentu', user=self.users['presidente']).exists())

	def test_access_is_limited_by_scope_and_role(self):
		self.login('sekrsukub')
		self.assertEqual(self.client.get(self.url('eleitoral')).status_code, 404)
		self.assertEqual(self.client.get(self.url('foto')).status_code, 404)
		self.login('admin')
		self.assertEqual(self.client.get(self.url('foto')).status_code, 403)
		self.login('koordsuku')
		self.assertEqual(self.client.get(self.url('foto')).status_code, 200)
		self.client.logout()
		resp = self.client.get(self.url('foto'))
		self.assertEqual(resp.status_code, 302)
		self.assertIn('/login/', resp['Location'])

	def test_unknown_kind_and_missing_file_are_404(self):
		self.login('presidente')
		self.assertEqual(self.client.get(self.url('rahasia')).status_code, 404)
		self.assertEqual(self.client.get('/membro/%s/file/..%%2F..%%2Fetc%%2Fpasswd/' % self.m.hashed).status_code, 404)
		other = self.make('UP00099')
		self.assertEqual(self.client.get(self.url('foto', other)).status_code, 404)

	def test_detail_page_uses_protected_urls(self):
		self.login('presidente')
		resp = self.client.get(reverse('membro-detail', args=[self.m.hashed]))
		self.assertContains(resp, self.url('foto'))
		self.assertContains(resp, self.url('eleitoral'))
		self.assertNotContains(resp, self.m.image.name)
		self.assertNotContains(resp, '/media/')


class ReplaceAndDeleteFilesTests(UploadBase):
	def setUp(self):
		self.post_member(image=self.jpg(), pdf=self.pdf())
		self.m = Membro.objects.get(nu_eleitoral='UP00001')

	def test_replacing_files_deletes_old_ones(self):
		old_img, old_pdf = self.m.image.path, self.m.file_eleitoral.path
		import os
		self.login('sekrsuku')
		data = self.form_data(nu='UP00001')
		data.update({'image': self.jpg(color=(200, 0, 0)), 'file_eleitoral': self.pdf(pages=2)})
		self.client.post(reverse('membro-update', args=[self.m.hashed]), data)
		self.m.refresh_from_db()
		self.assertNotEqual(self.m.image.path, old_img)
		self.assertFalse(os.path.exists(old_img))
		self.assertFalse(os.path.exists(old_pdf))
		self.assertTrue(os.path.exists(self.m.image.path))
		self.assertTrue(os.path.exists(self.m.file_eleitoral.path))

	def test_edit_without_new_files_keeps_existing(self):
		import os
		img, pdf = self.m.image.name, self.m.file_eleitoral.name
		self.login('sekrsuku')
		self.client.post(reverse('membro-update', args=[self.m.hashed]), self.form_data(nu='UP00001', nome='Nama Baru'))
		self.m.refresh_from_db()
		self.assertEqual((self.m.nome, self.m.image.name, self.m.file_eleitoral.name), ('Nama Baru', img, pdf))
		self.assertTrue(os.path.exists(self.m.image.path))

	def test_rejected_replacement_keeps_old_files(self):
		import os
		self.login('sekrsuku')
		data = self.form_data(nu='UP00001')
		data['file_eleitoral'] = SimpleUploadedFile('x.pdf', b'palsu', content_type='application/pdf')
		resp = self.client.post(reverse('membro-update', args=[self.m.hashed]), data)
		self.assertEqual(resp.status_code, 200)
		self.assertTrue(os.path.exists(self.m.file_eleitoral.path))

	def test_deleting_member_removes_both_files(self):
		import os
		paths = [self.m.image.path, self.m.file_eleitoral.path]
		self.login('presidente')
		self.client.post(reverse('membro-del', args=[self.m.hashed]))
		for p in paths:
			self.assertFalse(os.path.exists(p))

	def test_historia_records_file_change_without_leaking_full_name(self):
		self.login('sekrsuku')
		data = self.form_data(nu='UP00001')
		data['file_eleitoral'] = self.pdf(pages=3)
		self.client.post(reverse('membro-update', args=[self.m.hashed]), data)
		h = Historia.objects.filter(membro=self.m, aksaun='Edita').first()
		self.assertIn('Kartaun Eleitoral', h.detalhe)
		self.assertNotRegex(h.detalhe, r'[0-9a-f]{64}')


class VarandaTests(BaseCase):
	def setUp(self):
		self.opd = Organizasaun.objects.create(code='OPD', name='OPD')
		self.make('VR00001', self.va, self.a1, organizasaun=self.org, sex='Mane', aprovasaun='Aprovadu')
		self.make('VR00002', self.va, self.a2, sex='Feto', aprovasaun='Pendente')
		self.make('VR00003', self.vb, self.b1, organizasaun=self.org, sex='Mane', aprovasaun='Rejeitadu')

	def home(self, user):
		self.login(user)
		resp = self.client.get('/')
		self.assertEqual(resp.status_code, 200)
		return resp

	def table(self, resp, title):
		return [t for t in resp.context['tables'] if t['title'] == title][0]

	def test_postu_roles_see_suku_and_organizasaun_tables(self):
		for u in ('presidente', 'koordpostu', 'sekrpostu'):
			resp = self.home(u)
			self.assertEqual([t['title'] for t in resp.context['tables']], ['Suku', 'Organizasaun'], u)
			self.assertEqual(resp.context['banner'][1], 'POSTU DOM ALEIXO')
		suku = {r['name']: r for r in self.table(resp, 'Suku')['rows']}
		self.assertEqual((suku['Suku A']['total'], suku['Suku A']['mane'], suku['Suku A']['feto'], suku['Suku B']['rejeitadu']), (2, 1, 1, 1))
		org = {r['name']: r for r in self.table(resp, 'Organizasaun')['rows']}
		self.assertEqual((org['OJD']['total'], org['Laiha organizasaun']['total']), (2, 1))

	def test_cells_link_to_filtered_list(self):
		resp = self.home('presidente')
		row = [r for r in self.table(resp, 'Suku')['rows'] if r['name'] == 'Suku A'][0]
		urls = [u for _, u in row['cells']]
		self.assertEqual(urls[0], '/membro/?village=%d' % self.va.pk)
		self.assertIn('sex=Mane', urls[1])
		self.assertIn('aprovasaun=Pendente', urls[4])
		none_org = [r for r in self.table(resp, 'Organizasaun')['rows'] if r['name'] == 'Laiha organizasaun'][0]
		self.assertEqual(none_org['cells'][0][1], '/membro/?organizasaun=0')
		total = self.table(resp, 'Suku')['total_cells']
		self.assertEqual([v for v, _ in total], [3, 2, 1, 1, 1, 1])

	def test_organizasaun_zero_filter_lists_members_without_org(self):
		self.login('presidente')
		objs = self.client.get(reverse('membro-list') + '?organizasaun=0').context['objects']
		self.assertEqual([m.nu_eleitoral for m in objs], ['VR00002'])

	def test_suku_roles_see_only_their_aldeia_rows(self):
		for u in ('koordsuku', 'sekrsuku'):
			resp = self.home(u)
			self.assertEqual([t['title'] for t in resp.context['tables']], ['Aldeia'])
			self.assertEqual({r['name'] for r in self.table(resp, 'Aldeia')['rows']}, {'A1', 'A2'})
			self.assertEqual(resp.context['banner'][1], 'SUKU SUKU A')
			self.assertEqual(resp.context['chart_url'], reverse('api-aldeia'))

	def test_aldeia_roles_see_organizasaun_breakdown_of_own_aldeia(self):
		resp = self.home('sekraldeia')
		self.assertEqual([t['title'] for t in resp.context['tables']], ['Organizasaun'])
		self.assertEqual([(r['name'], r['total']) for r in self.table(resp, 'Organizasaun')['rows']], [('OJD', 1)])
		self.assertIn('ALDEIA A1', resp.context['banner'][1])

	def test_org_roles_see_suku_breakdown_of_their_members_only(self):
		for u in ('koordorg', 'sekrorg'):
			resp = self.home(u)
			self.assertEqual({(r['name'], r['total']) for r in self.table(resp, 'Suku')['rows']}, {('Suku A', 1), ('Suku B', 1)})
			self.assertEqual(resp.context['banner'][1], 'ORGANIZASAUN OJD')
			self.assertEqual(resp.context['tot']['total'], 2)

	def test_buttons_follow_role(self):
		self.assertContains(self.home('sekrsuku'), 'Aumenta Membru')
		self.assertContains(self.home('sekrorg'), 'Aumenta Membru')
		self.assertNotContains(self.home('koordsuku'), 'Aumenta Membru')
		resp = self.home('presidente')
		self.assertNotContains(resp, 'Aumenta Membru')
		self.assertContains(resp, 'Hein Aprovasaun (1)')
		self.assertContains(resp, 'Lista Jeral Membru')
		self.assertContains(resp, 'Relatoriu Tabular')

	def test_member_home_has_chart_and_local_highcharts(self):
		resp = self.home('presidente')
		self.assertContains(resp, 'id="chart_home"')
		self.assertContains(resp, 'js_custom/highcharts.js')
		self.assertContains(resp, '/report/api/suku/')
		self.assertNotContains(resp, 'Chart.min.js')
		self.assertNotContains(resp, 'https://')

	def test_admin_home_has_no_member_data(self):
		resp = self.home('admin')
		self.assertEqual(resp.context['kind'], 'admin')
		self.assertNotIn('tables', resp.context)
		roles_count = dict(resp.context['users_by_role'])
		self.assertEqual(roles_count['Sekretariu Organizasaun'], 1)
		self.assertEqual(resp.context['users_total'], 10)
		self.assertNotContains(resp, 'chart_home')
		self.assertNotContains(resp, 'Membru Por')

	def test_user_without_role_gets_notice(self):
		User.objects.create_user('tanpa', password='Teste-12345!')
		self.client.login(username='tanpa', password='Teste-12345!')
		self.assertContains(self.client.get('/'), 'seidauk iha peran')


class SekrOrgInputTests(BaseCase):
	def setUp(self):
		self.opd = Organizasaun.objects.create(code='OPD', name='OPD')
		self.own = self.make('OR00001', self.va, self.a1, organizasaun=self.org)
		self.other = self.make('OR00002', self.vb, self.b1, organizasaun=self.opd)

	def data(self, nu, **kw):
		d = self.form_data(nu=nu, **kw)
		d['village'] = self.va.pk
		return d

	def test_form_locks_organizasaun_and_leaves_suku_free(self):
		from membro.forms import MembroForm
		form = MembroForm(user=self.users['sekrorg'])
		self.assertTrue(form.fields['organizasaun'].disabled)
		self.assertEqual(form.fields['organizasaun'].initial, self.org.pk)
		self.assertFalse(form.fields['village'].disabled)
		self.assertEqual(form.fields['village'].queryset.count(), 2)
		self.assertEqual(form.fields['aldeia'].queryset.count(), 0)  # diisi lewat dropdown berantai
		self.login('sekrorg')
		self.assertContains(self.client.get(reverse('membro-add')), 'data-aldeias-url')

	def test_creates_member_in_own_organization_even_if_other_is_posted(self):
		self.login('sekrorg')
		resp = self.client.post(reverse('membro-add'), self.data('OR10001', organizasaun=self.opd.pk))
		self.assertEqual(resp.status_code, 302)
		m = Membro.objects.get(nu_eleitoral='OR10001')
		self.assertEqual((m.organizasaun, m.village, m.aldeia, m.aprovasaun, m.user.username), (self.org, self.va, self.a1, 'Pendente', 'sekrorg'))
		self.assertTrue(Historia.objects.filter(membro=m, aksaun='Kria').exists())

	def test_can_register_member_from_any_suku(self):
		self.login('sekrorg')
		d = self.data('OR10002')
		d.update({'village': self.vb.pk, 'aldeia': self.b1.pk})
		self.assertEqual(self.client.post(reverse('membro-add'), d).status_code, 302)
		self.assertEqual(Membro.objects.get(nu_eleitoral='OR10002').village, self.vb)

	def test_aldeia_must_belong_to_chosen_suku(self):
		self.login('sekrorg')
		d = self.data('OR10003')
		d['aldeia'] = self.b1.pk  # aldeia suku B, village suku A
		self.assertEqual(self.client.post(reverse('membro-add'), d).status_code, 200)
		self.assertFalse(Membro.objects.filter(nu_eleitoral='OR10003').exists())

	def test_duplicate_eleitoral_still_blocked(self):
		self.login('sekrorg')
		resp = self.client.post(reverse('membro-add'), self.data('or00002'))
		self.assertContains(resp, 'DUPLIKADU')

	def test_list_and_edit_limited_to_own_organization(self):
		self.login('sekrorg')
		listed = {m.nu_eleitoral for m in self.client.get(reverse('membro-list')).context['objects']}
		self.assertEqual(listed, {'OR00001'})
		self.assertEqual(self.client.get(reverse('membro-update', args=[self.other.hashed])).status_code, 404)
		resp = self.client.post(reverse('membro-update', args=[self.own.hashed]), self.data('OR00001', nome='Nama Baru'))
		self.assertEqual(resp.status_code, 302)
		self.own.refresh_from_db()
		self.assertEqual((self.own.nome, self.own.organizasaun, self.own.aprovasaun), ('Nama Baru', self.org, 'Pendente'))

	def test_cannot_move_member_to_other_organization_on_edit(self):
		self.login('sekrorg')
		self.client.post(reverse('membro-update', args=[self.own.hashed]), self.data('OR00001', organizasaun=self.opd.pk))
		self.own.refresh_from_db()
		self.assertEqual(self.own.organizasaun, self.org)

	def test_koordorg_still_view_only_and_cannot_approve(self):
		self.login('koordorg')
		self.assertEqual(self.client.get(reverse('membro-add')).status_code, 403)
		self.login('sekrorg')
		self.assertEqual(self.client.post(reverse('aprovasaun-aprova', args=[self.own.hashed])).status_code, 403)

	def test_gets_rejection_notifications_for_own_organization(self):
		Membro.objects.filter(pk=self.own.pk).update(aprovasaun='Rejeitadu')
		Membro.objects.filter(pk=self.other.pk).update(aprovasaun='Rejeitadu')
		self.login('sekrorg')
		self.assertEqual(self.client.get(reverse('api-notif-badge')).json()['rejeitadu'], 1)


class MetaTagTests(BaseCase):
	def test_login_page_has_complete_meta_tags(self):
		resp = self.client.get(reverse('login'))
		for needle in ('<meta charset="utf-8">', 'name="viewport"', 'name="description"', 'name="keywords"', 'name="author"',
				'name="robots" content="noindex, nofollow', 'name="theme-color" content="#0b1e8a"', 'property="og:title"',
				'property="og:description"', 'property="og:image" content="http://testserver/static/main/images/bandeira_pd.png"',
				'name="twitter:card"', 'rel="apple-touch-icon"', 'rel="icon"', 'name="referrer" content="same-origin"'):
			self.assertContains(resp, needle)

	def test_page_specific_title_and_description(self):
		self.login('presidente')
		resp = self.client.get('/')
		self.assertContains(resp, '<title>SGDM-PDPADA - Varanda</title>')
		self.assertContains(resp, 'content="Varanda SGDM-PDPADA: rekapitulasaun membru')
		self.assertContains(resp, 'property="og:url" content="http://testserver/"')

	def test_robots_txt_disallows_everything(self):
		resp = self.client.get('/robots.txt')
		self.assertEqual((resp.status_code, resp['Content-Type']), (200, 'text/plain'))
		self.assertContains(resp, 'Disallow: /')

	def test_chart_page_has_new_highcharts_cards(self):
		self.login('presidente')
		resp = self.client.get(reverse('report-chart'))
		for cid in ('chart_umur', 'chart_marital', 'chart_hakbit'):
			self.assertContains(resp, f'id="{cid}"')


class TabularTests(BaseCase):
	def setUp(self):
		d = datetime.date.today()
		self.make('TB00001', self.va, self.a1, organizasaun=self.org, sex='Mane', marital='Casado/a',
			date_of_birth=d.replace(year=d.year - 30), data_hakbit=datetime.date(2015, 1, 1), aprovasaun='Aprovadu')
		self.make('TB00002', self.va, self.a2, sex='Feto', date_of_birth=d.replace(year=d.year - 22), status='Inativu')
		self.make('TB00003', self.vb, self.b1, sex='Feto', marital='Viuvo/a', date_of_birth=d.replace(year=d.year - 70), data_hakbit=datetime.date(2015, 6, 1))

	def page(self, user):
		self.login(user)
		resp = self.client.get(reverse('report-dash'))
		self.assertEqual(resp.status_code, 200)
		return resp

	def table(self, resp, head):
		return {r['name']: r for r in [t for t in resp.context['tables'] if t['head'] == head][0]['rows']}

	def test_layout_follows_sample(self):
		resp = self.page('presidente')
		self.assertEqual([t['head'] for t in resp.context['tables']], ['Suku', 'Aldeia', 'Organizasaun', 'Tinan', 'Idade', 'Estado Civil'])
		self.assertContains(resp, 'card-header bg-warning')
		self.assertContains(resp, 'th-amber')
		self.assertContains(resp, 'REKAPITULASAUN MEMBRU PD')
		self.assertEqual(resp.context['tot']['total'], 3)
		self.assertEqual((resp.context['tot']['ativu'], resp.context['tot']['inativu'], resp.context['tot']['falesidu']), (2, 1, 0))

	def test_tables_values_and_links(self):
		resp = self.page('presidente')
		self.assertEqual((self.table(resp, 'Suku')['Suku A']['total'], self.table(resp, 'Suku')['Suku B']['total']), (2, 1))
		self.assertEqual(self.table(resp, 'Suku')['Suku A']['url'], '/membro/?village=%d' % self.va.pk)
		self.assertEqual(self.table(resp, 'Tinan')['2015']['total'], 2)
		self.assertEqual(self.table(resp, 'Tinan')['2015']['url'], '/membro/?hakbit=2015')
		self.assertEqual(self.table(resp, 'Organizasaun')['Laiha organizasaun']['url'], '/membro/?organizasaun=0')
		self.assertEqual(self.table(resp, 'Estado Civil')['Laiha']['url'], '/membro/?marital=laiha')
		self.assertEqual({k: v['total'] for k, v in self.table(resp, 'Idade').items()}, {'18-25': 1, '26-35': 1, '> 65': 1})

	def test_suku_user_sees_only_own_data(self):
		resp = self.page('koordsuku')
		self.assertEqual(set(self.table(resp, 'Suku')), {'Suku A'})
		self.assertEqual(set(self.table(resp, 'Aldeia')), {'A1', 'A2'})
		self.assertEqual(resp.context['tot']['total'], 2)

	def test_links_filter_the_member_list(self):
		self.login('presidente')
		get = lambda q: {m.nu_eleitoral for m in self.client.get(reverse('membro-list') + q).context['objects']}
		self.assertEqual(get('?marital=laiha'), {'TB00002'})
		self.assertEqual(get('?marital=Viuvo/a'), {'TB00003'})
		self.assertEqual(get('?umur=18-25'), {'TB00002'})
		self.assertEqual(get('?umur=26-35'), {'TB00001'})
		self.assertEqual(get('?umur=%3E+65'), {'TB00003'})
		self.assertEqual(get('?umur=bukan-bin'), {'TB00001', 'TB00002', 'TB00003'})
		self.assertEqual(get('?hakbit=2015'), {'TB00001', 'TB00003'})

	def test_age_filter_matches_age_api(self):
		self.login('presidente')
		api = self.client.get(reverse('api-age')).json()
		for label, n in zip(api['label'], api['obj']):
			listed = self.client.get(reverse('membro-list'), {'umur': label}).context['objects']
			self.assertEqual(len(listed), n, label)

	def test_admin_forbidden(self):
		self.login('admin')
		self.assertEqual(self.client.get(reverse('report-dash')).status_code, 403)


class RelatoriuMenuTests(BaseCase):
	def test_dropdown_in_navbar_and_sidebar(self):
		self.login('presidente')
		resp = self.client.get('/')
		self.assertContains(resp, 'Relatoriu</a>')
		self.assertContains(resp, 'href="/report/"><i class="fa fa-table"></i> Tabular')
		self.assertContains(resp, 'href="/report/chart/"><i class="fa fa-bar-chart"></i> Grafiku')
		self.assertContains(resp, '<li class="sb-sec">Relatoriu</li>')
		self.assertNotContains(resp, '> Rekap<')

	def test_chart_page_breadcrumb_points_to_tabular(self):
		self.login('presidente')
		resp = self.client.get(reverse('report-chart'))
		self.assertContains(resp, '>TABULAR</a>')
		self.assertContains(resp, 'RELATORIU GRAFIKU')


class MissingFilesTextTests(BaseCase):
	def test_texts_when_no_files(self):
		m = self.make('MF00001')
		self.login('presidente')
		detail = self.client.get(reverse('membro-detail', args=[m.hashed]))
		self.assertContains(detail, 'Seidauk upload eleitoral')
		self.assertContains(detail, 'Seidauk upload fotu')
		self.assertNotContains(detail, 'Hare PDF')
		lst = self.client.get(reverse('membro-list'))
		self.assertContains(lst, 'ELEITORAL (PDF)')
		self.assertContains(lst, 'Seidauk upload')


class MissingFilesTextWithFilesTests(UploadBase):
	def test_no_missing_text_when_files_exist(self):
		self.post_member(nu='MF00002', image=self.jpg(), pdf=self.pdf())
		m = Membro.objects.get(nu_eleitoral='MF00002')
		self.login('presidente')
		detail = self.client.get(reverse('membro-detail', args=[m.hashed]))
		self.assertNotContains(detail, 'Seidauk upload')
		self.assertContains(detail, 'Hare PDF')
		self.assertNotContains(self.client.get(reverse('membro-list')), 'Seidauk upload')


class UpdateScriptTests(BaseCase):
	def test_update_script_runs_migrate(self):
		import os
		path = os.path.join(settings.BASE_DIR, 'update.sh')
		self.assertTrue(os.access(path, os.X_OK))
		content = open(path).read()
		for step in ('git pull', 'pip install -r requirements.txt', 'migrate', 'collectstatic', 'set -euo pipefail'):
			self.assertIn(step, content)


class LoginPageTests(BaseCase):
	def test_login_layout_follows_sample(self):
		resp = self.client.get(reverse('login'))
		self.assertEqual(resp.status_code, 200)
		for needle in ('SISTEMA JESTAUN DADUS MEMBRU', 'PARTIDO DEMOCRATICO', 'SGDM-PDPADA', 'class="card border-primary shadow-lg"',
				'card-header bg-primary text-white', 'LOGIN', 'Log In', 'name="username"', 'name="password"', 'csrfmiddlewaretoken'):
			self.assertContains(resp, needle)

	def test_login_shows_full_flag_not_cropped_logo(self):
		resp = self.client.get(reverse('login'))
		self.assertContains(resp, 'class="login-flag" src="/static/main/images/bandeira_pd.png"')
		self.assertContains(resp, 'width="592" height="337"')
		self.assertNotContains(resp, 'logo_pd')

	def test_flag_file_is_complete_and_not_cropped(self):
		import os
		base = os.path.join(settings.BASE_DIR, 'main/static/main/images')
		with Image.open(os.path.join(base, 'bandeira_pd.png')) as flag:
			self.assertEqual(flag.size, (592, 337))  # ukuran bendera asli utuh
		self.assertFalse(os.path.exists(os.path.join(base, 'logo_pd.png')))  # potongan emblem tidak dipakai lagi

	def test_icons_keep_the_whole_flag_with_padding(self):
		import os
		base = os.path.join(settings.BASE_DIR, 'main/static/main/images')
		with Image.open(os.path.join(base, 'favicon.png')) as fav:
			self.assertEqual(fav.size, (64, 64))
			rgba = fav.convert('RGBA')
			self.assertEqual(rgba.getpixel((0, 0))[3], 0)        # sudut atas transparan (padding)
			self.assertGreater(rgba.getpixel((0, 32))[3], 200)   # tepi kiri bendera terisi penuh: tidak terpotong
			self.assertGreater(rgba.getpixel((63, 32))[3], 200)  # tepi kanan bendera terisi penuh
		with Image.open(os.path.join(base, 'apple-touch-icon.png')) as apple:
			self.assertEqual(apple.size, (180, 180))

	def test_navbar_uses_full_flag(self):
		self.login('presidente')
		resp = self.client.get('/')
		self.assertContains(resp, 'class="brand-flag" src="/static/main/images/bandeira_pd.png"')
		self.assertNotContains(resp, 'logo_pd')
		self.assertContains(resp, 'apple-touch-icon.png')

	def test_login_error_message_and_authentication(self):
		bad = self.client.post(reverse('login'), {'username': 'presidente', 'password': 'salah'})
		self.assertContains(bad, 'Username ka password la loos.')
		ok = self.client.post(reverse('login'), {'username': 'presidente', 'password': 'Teste-12345!'})
		self.assertRedirects(ok, '/', fetch_redirect_response=False)

	def test_logged_in_user_is_redirected_from_login(self):
		self.login('presidente')
		self.assertEqual(self.client.get(reverse('login')).status_code, 302)
