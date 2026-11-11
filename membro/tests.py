import datetime
import os
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
		for u in ('presidente', 'koordpostu'):
			self.assertEqual(self.names(u), {'SCOPE01', 'SCOPE02', 'SCOPE03'})

	def test_sekretariu_postu_only_sees_recap_not_member_data(self):
		self.login('sekrpostu')
		for name, args in [('membro-list', ()), ('membro-cari', ()), ('alokasaun-dash', ()), ('historia-list', ()),
				('membro-detail', (self.ma1.hashed,)), ('membro-file', (self.ma1.hashed, 'foto')), ('api-membro-cari', ())]:
			self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 403, name)
		for name in ('home', 'membro-painel', 'report-dash', 'report-chart'):
			self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

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
		self.assertEqual(self.menu('admin'), ['Varanda', 'Painel', 'Uzuáriu', 'Data Master', 'Historia'])
		self.assertEqual(self.menu('presidente'),
			['Varanda', 'Painel', 'Membru', 'Relatoriu', 'Struktura', 'Historia'])
		self.assertEqual(self.menu('sekrsuku'), ['Varanda', 'Painel', 'Membru', 'Relatoriu', 'Struktura'])
		self.assertEqual(self.menu('sekrorg'), ['Varanda', 'Painel', 'Membru', 'Relatoriu', 'Struktura'])
		self.assertEqual(self.menu('koordsuku'), ['Varanda', 'Painel', 'Membru', 'Relatoriu', 'Struktura'])

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
from django.test import override_settings, TransactionTestCase
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


class PainelTests(BaseCase):
	def setUp(self):
		self.opd = Organizasaun.objects.create(code='OPD', name='OPD')
		self.make('VR00001', self.va, self.a1, organizasaun=self.org, sex='Mane', aprovasaun='Aprovadu')
		self.make('VR00002', self.va, self.a2, sex='Feto', aprovasaun='Pendente')
		self.make('VR00003', self.vb, self.b1, organizasaun=self.org, sex='Mane', aprovasaun='Rejeitadu')

	def home(self, user):
		self.login(user)
		resp = self.client.get(reverse('membro-painel'))
		self.assertEqual(resp.status_code, 200)
		return resp

	def table(self, resp, title):
		return [t for t in resp.context['tables'] if t['title'] == title][0]

	def test_postu_roles_see_year_suku_chart_panel(self):
		for u in ('presidente', 'koordpostu', 'sekrpostu'):
			resp = self.home(u)
			self.assertTemplateUsed(resp, 'membro/painel_postu.html')
			self.assertContains(resp, 'id="chart_painel"')
			self.assertContains(resp, 'js_custom/highcharts.js')
			self.assertNotContains(resp, 'https://')
			suku = {r['obj'].name: r for r in resp.context['objects2']}
			self.assertEqual((suku['Suku A']['n'], suku['Suku A']['mane'], suku['Suku A']['feto'], suku['Suku B']['n']), (2, 1, 1, 1), u)
			self.assertEqual(resp.context['chart'], {'label': ['Suku A', 'Suku B'], 'obj': [2, 1], 'selected': -1}, u)
			self.assertEqual([(y.year, n, a) for y, n, a in resp.context['objects1']], [(2026, 3, True)], u)

	def test_postu_painel_selects_suku_and_links_only_for_list_roles(self):
		url = reverse('membro-painel') + '?ano=%d&suku=%d' % (self.year.pk, self.va.pk)
		self.login('presidente')
		resp = self.client.get(url)
		self.assertEqual(resp.context['chart']['selected'], 0)
		self.assertEqual([(a.name, n) for a, n, _ in resp.context['aldeias']], [('A1', 1), ('A2', 1)])
		self.assertEqual(resp.context['aldeias'][0][2], '/membro/?aldeia=%d' % self.a1.pk)
		self.login('sekrpostu')
		resp = self.client.get(url)
		self.assertEqual({u for _, _, u in resp.context['aldeias']}, {''})
		self.assertNotContains(resp, '/membro/?')

	def test_postu_painel_ignores_invalid_parameters(self):
		self.login('presidente')
		resp = self.client.get(reverse('membro-painel') + '?ano=abc&suku=zzz')
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(resp.context['ano'], self.year)
		self.assertIsNone(resp.context['selected'])

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
		resp = self.home('sekraldeia')
		self.assertContains(resp, 'Lista Jeral Membru')
		self.assertContains(resp, 'Relatoriu Tabular')
		self.assertNotContains(resp, reverse('aprovasaun-list'))

	def test_member_home_has_chart_and_local_highcharts(self):
		resp = self.home('sekraldeia')
		self.assertContains(resp, 'id="chart_home"')
		self.assertContains(resp, 'js_custom/highcharts.js')
		self.assertContains(resp, '/report/api/organizasaun/')
		self.assertNotContains(resp, 'Chart.min.js')
		self.assertNotContains(resp, 'https://')



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
		self.login('sekrsuku')
		resp = self.client.get('/')
		self.assertContains(resp, '<title>SGDM-PDPADA - Varanda</title>')
		self.assertContains(resp, 'content="SGDM-PDPADA: Sistema Jestaun Dadus Membru Partido Democratico')
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
		self.assertContains(lst, 'DOKUMENTU')
		self.assertContains(lst, 'Seidauk upload fotu')
		self.assertContains(lst, 'Seidauk upload eleitoral')
		self.assertContains(lst, 'class="doc no"')


class MissingFilesTextWithFilesTests(UploadBase):
	def test_no_missing_text_when_files_exist(self):
		self.post_member(nu='MF00002', image=self.jpg(), pdf=self.pdf())
		m = Membro.objects.get(nu_eleitoral='MF00002')
		self.login('presidente')
		detail = self.client.get(reverse('membro-detail', args=[m.hashed]))
		self.assertNotContains(detail, 'Seidauk upload')
		self.assertContains(detail, 'Hare PDF')
		lst = self.client.get(reverse('membro-list'))
		self.assertNotContains(lst, 'Seidauk upload')
		self.assertContains(lst, 'class="doc ok"')


class UpdateScriptTests(BaseCase):
	def test_update_script_runs_every_step(self):
		import os
		path = os.path.join(settings.BASE_DIR, 'update.sh')
		self.assertTrue(os.access(path, os.X_OK))
		content = open(path).read()
		for step in ('git fetch', '--ff-only', 'pip install -r requirements.txt', 'migrate', 'collectstatic', 'manage.py check',
				'set -euo pipefail', '--reset'):
			self.assertIn(step, content)


class UpdateScriptGitBehaviourTests(BaseCase):
	"""Menjalankan update.sh sungguhan di repo git sementara (bagian aplikasi dilewati)."""

	def sh(self, *args, cwd, check=True):
		import subprocess
		env = dict(os.environ, GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@t', GIT_COMMITTER_NAME='t', GIT_COMMITTER_EMAIL='t@t',
			UPDATE_SKIP_APP='1')
		res = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True)
		if check:
			self.assertEqual(res.returncode, 0, res.stderr + res.stdout)
		return res

	def setUp(self):
		self.root = tempfile.mkdtemp(prefix='pdpada-upd-')
		self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
		self.origin = os.path.join(self.root, 'origin.git')
		self.work = os.path.join(self.root, 'work')       # tempat developer
		self.server = os.path.join(self.root, 'server')   # meniru PythonAnywhere
		self.sh('git', 'init', '--bare', '-b', 'main', self.origin, cwd=self.root)
		self.sh('git', 'clone', self.origin, self.work, cwd=self.root)
		self.sh('git', 'checkout', '-b', 'main', cwd=self.work, check=False)
		with open(os.path.join(self.work, 'a.txt'), 'w') as f:
			f.write('satu\n')
		shutil.copy(os.path.join(settings.BASE_DIR, 'update.sh'), os.path.join(self.work, 'update.sh'))
		self.sh('git', 'add', '-A', cwd=self.work)
		self.sh('git', 'commit', '-m', 'awal', cwd=self.work)
		self.sh('git', 'push', '-u', 'origin', 'main', cwd=self.work)
		self.sh('git', 'clone', self.origin, self.server, cwd=self.root)
		with open(os.path.join(self.server, '.env'), 'w') as f:   # file tak dilacak (rahasia server)
			f.write('RAHASIA=1\n')

	def push_change(self, text='dua\n'):
		with open(os.path.join(self.work, 'a.txt'), 'a') as f:
			f.write(text)
		self.sh('git', 'commit', '-am', 'ubah', cwd=self.work)
		self.sh('git', 'push', cwd=self.work)

	def head(self, cwd):
		return self.sh('git', 'rev-parse', 'HEAD', cwd=cwd).stdout.strip()

	def test_normal_update_fast_forwards(self):
		self.push_change()
		res = self.sh('bash', 'update.sh', cwd=self.server)
		self.assertIn('Reload', res.stdout)
		self.assertEqual(self.head(self.server), self.head(self.work))

	def test_diverged_server_gets_clear_hint_and_is_not_modified(self):
		self.sh('git', 'checkout', '-b', 'fitur', cwd=self.work)
		with open(os.path.join(self.work, 'b.txt'), 'w') as f:
			f.write('fitur\n')
		self.sh('git', 'add', '-A', cwd=self.work)
		self.sh('git', 'commit', '-m', 'fitur', cwd=self.work)
		self.sh('git', 'push', '-u', 'origin', 'fitur', cwd=self.work)
		# server menarik branch fitur ke main lokal -> commit gabungan lokal
		self.sh('git', 'pull', '--no-rebase', '--no-edit', 'origin', 'fitur', cwd=self.server)
		self.sh('git', 'checkout', 'main', cwd=self.work)
		self.push_change('dari-main\n')
		before = self.head(self.server)
		res = self.sh('bash', 'update.sh', cwd=self.server, check=False)
		self.assertNotEqual(res.returncode, 0)
		self.assertIn('--reset', res.stderr)
		self.assertEqual(self.head(self.server), before)

	def test_reset_realigns_with_github_and_keeps_untracked_files(self):
		self.sh('git', 'checkout', '-b', 'fitur', cwd=self.work)
		with open(os.path.join(self.work, 'b.txt'), 'w') as f:
			f.write('fitur\n')
		self.sh('git', 'add', '-A', cwd=self.work)
		self.sh('git', 'commit', '-m', 'fitur', cwd=self.work)
		self.sh('git', 'push', '-u', 'origin', 'fitur', cwd=self.work)
		self.sh('git', 'pull', '--no-rebase', '--no-edit', 'origin', 'fitur', cwd=self.server)
		self.sh('git', 'checkout', 'main', cwd=self.work)
		self.push_change('dari-main\n')
		self.sh('bash', 'update.sh', '--reset', cwd=self.server)
		self.assertEqual(self.head(self.server), self.head(self.work))
		self.assertEqual(open(os.path.join(self.server, '.env')).read(), 'RAHASIA=1\n')  # tidak tersentuh

	def test_reset_refuses_when_tracked_files_were_edited(self):
		with open(os.path.join(self.server, 'a.txt'), 'a') as f:
			f.write('EDIT-LOKAL\n')
		self.push_change()
		res = self.sh('bash', 'update.sh', '--reset', cwd=self.server, check=False)
		self.assertNotEqual(res.returncode, 0)
		self.assertIn('perubahan lokal', res.stderr)
		self.assertIn('EDIT-LOKAL', open(os.path.join(self.server, 'a.txt')).read())  # tidak dihapus



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


# ---------------------------------------------------------------- beranda, painel admin, fitur baru
import csv
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, connection
from django.test.utils import CaptureQueriesContext
import zipfile
from pathlib import Path
from django.db import transaction


class LandingTests(BaseCase):
	def tiles(self, user):
		self.login(user)
		resp = self.client.get('/')
		self.assertEqual(resp.status_code, 200)
		return resp, {t['title']: t for t in resp.context['tiles']}

	def test_hero_has_title_full_flag_and_welcome(self):
		resp, _ = self.tiles('sekrsuku')
		for needle in ('SISTEMA JESTAUN', 'SGDM-PDPADA', "Hanoin &middot; Hari'i &middot; Hametin", 'Utiliza husi', 'Sekjer Suku',
				'width="592" height="337"', 'bandeira_pd.png', 'Tinan 2026'):
			self.assertContains(resp, needle)
		self.assertNotContains(resp, 'logo_pd')

	def varanda(self, user):
		self.login(user)
		resp = self.client.get('/')
		self.assertEqual(resp.status_code, 200)
		self.assertTemplateUsed(resp, 'home/varanda_postu.html')
		return resp

	def test_postu_varanda_has_total_suku_line_aldeia_cards_and_chart(self):
		self.make('LD00001'); self.make('LD00002', self.vb, self.b1)
		for u in ('presidente', 'koordpostu', 'sekrpostu'):
			resp = self.varanda(u)
			self.assertEqual(resp.context['total'], 2, u)
			self.assertEqual([(v.name, n) for v, n in resp.context['objects1']], [('Suku A', 1), ('Suku B', 1)], u)
			self.assertEqual([(a['obj'].name, a['n']) for a in resp.context['objects2']], [('A1', 1), ('A2', 0), ('B1', 1)], u)
			self.assertEqual(resp.context['chart'], {'label': ['A1', 'A2', 'B1'], 'obj': [1, 0, 1]}, u)
			for needle in ('Utiliza husi', 'Total Membru', 'MEMBRU TUIR ALDEIA', 'id="chart_aldeia_postu"', 'js_custom/highcharts.js', 'width="296"'):
				self.assertContains(resp, needle)
			self.assertNotContains(resp, 'https://')

	def test_postu_varanda_links_and_search_follow_role(self):
		self.make('LD00001')
		resp = self.varanda('presidente')
		self.assertContains(resp, 'id="search-q"')
		self.assertContains(resp, '/membro/?aldeia=%d' % self.a1.pk)
		self.assertContains(resp, 'Hein Aprovasaun')
		resp = self.varanda('sekrpostu')  # Sekretariu Postu: rekapitulasi saja
		self.assertNotContains(resp, 'id="search-q"')
		self.assertNotContains(resp, '/membro/?')
		self.assertNotContains(resp, 'Lista Membru')
		self.assertNotContains(resp, 'Hein Aprovasaun')
		self.assertNotContains(resp, 'Struktura')

	def test_postu_varanda_query_count_is_constant(self):
		self.login('presidente')

		def count():
			with CaptureQueriesContext(connection) as ctx:
				self.client.get('/')
			return len(ctx)
		before = count()
		for i in range(10):
			self.make(f'LQ{i:04d}', aldeia=self.a2)
		self.assertEqual(count(), before)

	def test_tiles_for_secretaries_and_viewers(self):
		self.make('LD00003', aprovasaun='Rejeitadu')
		for u in ('sekrsuku', 'sekraldeia', 'sekrorg'):
			_, tiles = self.tiles(u)
			self.assertIn('Aumenta Membru', tiles, u)
			self.assertIn('Membru Rejeitadu', tiles, u)
			self.assertNotIn('Hein Aprovasaun', tiles, u)
			self.assertNotIn('Dupla Potensial', tiles, u)
		self.assertEqual(self.tiles('sekrsuku')[1]['Membru Rejeitadu']['badge'], 1)
		_, tiles = self.tiles('koordsuku')
		self.assertNotIn('Aumenta Membru', tiles)
		self.assertNotIn('Historia', tiles)

	def test_admin_tiles_have_no_member_features(self):
		resp, tiles = self.tiles('admin')
		self.assertEqual(set(tiles), {'Painel Admin', 'Uzuáriu', 'Suku no Aldeia', 'Organizasaun', 'Tinan Ativu', 'Historia'})
		self.assertFalse(resp.context['can_search'])
		self.assertNotContains(resp, 'id="search-q"')

	def test_search_box_only_for_member_roles(self):
		resp, _ = self.tiles('sekrsuku')
		self.assertContains(resp, 'id="search-q"')
		self.assertContains(resp, 'data-url="/membro/api/cari/"')

	def test_user_without_role_gets_notice(self):
		User.objects.create_user('tanpa', password='Teste-12345!')
		self.client.login(username='tanpa', password='Teste-12345!')
		self.assertContains(self.client.get('/'), 'seidauk iha peran')

	def test_landing_is_lightweight(self):
		self.login('sekrsuku')
		with CaptureQueriesContext(connection) as ctx:
			self.client.get('/')
		self.assertLessEqual(len(ctx), 14)
		self.assertFalse(any('GROUP BY' in q['sql'] for q in ctx.captured_queries))

	def test_requires_login(self):
		self.client.logout()
		self.assertEqual(self.client.get('/').status_code, 302)


class PainelAdminTests(BaseCase):
	def test_admin_panel_content(self):
		self.login('admin')
		resp = self.client.get(reverse('user-painel'))
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(dict(resp.context['users_by_role'])['Sekretariu Organizasaun'], 1)
		self.assertEqual(resp.context['users_total'], 10)
		self.assertNotContains(resp, 'Membru Por')

	def test_only_admin(self):
		for u in ('presidente', 'sekrsuku', 'koordorg'):
			self.login(u)
			self.assertEqual(self.client.get(reverse('user-painel')).status_code, 403, u)

	def test_member_panel_forbidden_for_admin(self):
		self.login('admin')
		self.assertEqual(self.client.get(reverse('membro-painel')).status_code, 403)


class SearchTests(BaseCase):
	def setUp(self):
		self.m1 = self.make('SR00001', self.va, self.a1, nome='Maria da Silva', telefone='77001234')
		self.m2 = self.make('SR00002', self.va, self.a2, nome='Jose Maria Soares')
		self.m3 = self.make('SR00003', self.vb, self.b1, nome='Maria Gomes', telefone='77001234')
		self.m4 = self.make('SR00004', self.va, self.a1, nome='<script>alert(1)</script> Hacker')

	def names(self, user, q, url=None):
		self.login(user)
		resp = self.client.get(url or reverse('membro-cari'), {'q': q})
		self.assertEqual(resp.status_code, 200)
		return resp, {m.nu_eleitoral for m in resp.context['objects']}

	def test_name_search_all_words_any_order_case_insensitive(self):
		self.assertEqual(self.names('presidente', 'maria silva')[1], {'SR00001'})
		self.assertEqual(self.names('presidente', 'SILVA MARIA')[1], {'SR00001'})
		self.assertEqual(self.names('presidente', 'maria')[1], {'SR00001', 'SR00002', 'SR00003'})

	def test_eleitoral_prefix_and_phone(self):
		self.assertEqual(self.names('presidente', 'sr0000')[1], {'SR00001', 'SR00002', 'SR00003', 'SR00004'})
		self.assertEqual(self.names('presidente', 'SR00002')[1], {'SR00002'})
		self.assertEqual(self.names('presidente', '77001234')[1], {'SR00001', 'SR00003'})
		self.assertEqual(self.names('presidente', '+670 7700 1234')[1], {'SR00001', 'SR00003'})

	def test_results_limited_to_user_scope(self):
		self.assertEqual(self.names('koordsuku', 'maria')[1], {'SR00001', 'SR00002'})  # Suku B tidak terlihat
		self.assertEqual(self.names('sekraldeia', 'maria')[1], {'SR00001'})
		self.assertEqual(self.names('koordorg', 'maria')[1], set())

	def test_short_query_and_empty_query(self):
		resp, found = self.names('presidente', 'm')
		self.assertEqual(found, set())
		self.assertContains(resp, 'Hakerek karakter 2 ka liu')
		resp, found = self.names('presidente', '')
		self.assertEqual(found, set())
		self.assertNotContains(resp, 'rezultadu')

	def test_html_in_names_is_escaped(self):
		resp, _ = self.names('presidente', 'hacker')
		self.assertNotContains(resp, '<script>alert(1)</script>')
		self.assertContains(resp, '&lt;script&gt;')

	def test_api_returns_max_8_with_detail_url(self):
		for i in range(10):
			self.make(f'SR1000{i}', nome=f'Pedro Teste {i}')
		self.login('presidente')
		data = self.client.get(reverse('api-membro-cari'), {'q': 'pedro teste'}).json()
		self.assertEqual(len(data), 8)
		self.assertEqual(set(data[0]), {'nome', 'nu_eleitoral', 'suku', 'aldeia', 'status', 'aprovasaun', 'url'})
		self.assertTrue(data[0]['url'].startswith('/membro/'))

	def test_api_scope_and_permissions(self):
		self.login('koordsuku')
		self.assertEqual({d['nu_eleitoral'] for d in self.client.get(reverse('api-membro-cari'), {'q': 'maria'}).json()}, {'SR00001', 'SR00002'})
		self.login('admin')
		self.assertEqual(self.client.get(reverse('api-membro-cari'), {'q': 'maria'}).status_code, 403)
		self.client.logout()
		self.assertIn(self.client.get(reverse('api-membro-cari'), {'q': 'maria'}).status_code, (401, 403))

	def test_page_forbidden_for_admin(self):
		self.login('admin')
		self.assertEqual(self.client.get(reverse('membro-cari')).status_code, 403)


class ExportTests(BaseCase):
	def setUp(self):
		self.make('EX00001', self.va, self.a1, nome='Ana Satu', sex='Feto', aprovasaun='Aprovadu')
		self.make('EX00002', self.vb, self.b1, nome='=HYPERLINK("http://jahat")', sex='Mane')
		self.make('EX00003', self.va, self.a2, nome='+cmd|calc', sex='Mane')

	def rows(self, user, query=''):
		self.login(user)
		resp = self.client.get(reverse('membro-export') + query)
		self.assertEqual(resp.status_code, 200)
		body = b''.join(resp.streaming_content).decode('utf-8')
		return resp, list(csv.reader(io.StringIO(body.lstrip('﻿'))))

	def test_roles(self):
		for u in ('presidente', 'koordpostu'):
			self.assertEqual(self.rows(u)[0].status_code, 200, u)
		for u in ('sekrpostu', 'sekrsuku', 'koordsuku', 'sekraldeia', 'koordorg', 'sekrorg', 'admin'):
			self.login(u)
			self.assertEqual(self.client.get(reverse('membro-export')).status_code, 403, u)
		self.client.logout()
		self.assertEqual(self.client.get(reverse('membro-export')).status_code, 302)

	def test_headers_bom_and_complete_content(self):
		resp, rows = self.rows('presidente')
		self.assertEqual(resp['Content-Type'], 'text/csv; charset=utf-8')
		self.assertRegex(resp['Content-Disposition'], r'^attachment; filename="membru-\d{8}-\d{4}\.csv"$')
		self.assertEqual(resp['Cache-Control'], 'private, no-store')
		self.assertEqual(rows[0][:3], ['Nu. Eleitoral', 'Naran', 'Sexu'])
		self.assertEqual({r[0] for r in rows[1:]}, {'EX00001', 'EX00002', 'EX00003'})

	def test_bom_present(self):
		self.login('presidente')
		raw = b''.join(self.client.get(reverse('membro-export')).streaming_content)
		self.assertTrue(raw.startswith(b'\xef\xbb\xbf'))

	def test_respects_filters_like_the_list(self):
		_, rows = self.rows('presidente', '?sex=Feto')
		self.assertEqual({r[0] for r in rows[1:]}, {'EX00001'})
		_, rows = self.rows('presidente', '?village=%d' % self.va.pk)
		self.assertEqual({r[0] for r in rows[1:]}, {'EX00001', 'EX00003'})
		self.login('presidente')
		listed = {m.nu_eleitoral for m in self.client.get(reverse('membro-list') + '?village=%d' % self.va.pk).context['objects']}
		self.assertEqual(listed, {r[0] for r in rows[1:]})

	def test_formula_injection_is_neutralised(self):
		_, rows = self.rows('presidente')
		names = {r[0]: r[1] for r in rows[1:]}
		self.assertEqual(names['EX00002'], "'=HYPERLINK(\"http://jahat\")")
		self.assertEqual(names['EX00003'], "'+cmd|calc")

	def test_export_is_audited(self):
		self.rows('presidente', '?sex=Mane')
		h = Historia.objects.get(aksaun='Ekspor')
		self.assertEqual(h.user, self.users['presidente'])
		self.assertIn('2 membru', h.detalhe)
		self.assertIn('sex=Mane', h.detalhe)

	def test_button_only_for_export_roles(self):
		self.login('presidente')
		self.assertContains(self.client.get(reverse('membro-list')), 'Ekspor CSV')
		self.login('sekrsuku')
		self.assertNotContains(self.client.get(reverse('membro-list')), 'Ekspor CSV')


class DuplicateReviewTests(BaseCase):
	def setUp(self):
		dob = datetime.date(1985, 7, 7)
		self.d1 = self.make('DP00001', self.va, self.a1, nome='Joao Pereira', date_of_birth=dob)
		self.d2 = self.make('DP00002', self.vb, self.b1, nome='JOAO PEREIRA', date_of_birth=dob)
		self.other_dob = self.make('DP00003', nome='Joao Pereira', date_of_birth=datetime.date(1990, 1, 1))
		self.t1 = self.make('DP00004', nome='Rosa Lopes', telefone='77889900')
		self.t2 = self.make('DP00005', self.vb, self.b1, nome='Elena Cruz', telefone='77889900')
		self.single = self.make('DP00006', nome='Unik Sekali', telefone='71112222')

	def page(self, user='presidente'):
		self.login(user)
		resp = self.client.get(reverse('membro-dupla'))
		self.assertEqual(resp.status_code, 200)
		return resp

	def test_groups_by_name_and_birth_date_case_insensitive(self):
		groups = self.page().context['groups_nome']
		self.assertEqual(len(groups), 1)
		self.assertEqual({m.nu_eleitoral for m in groups[0]}, {'DP00001', 'DP00002'})  # tanggal lahir lain tidak ikut

	def test_groups_by_phone(self):
		groups = self.page().context['groups_tel']
		self.assertEqual(len(groups), 1)
		self.assertEqual({m.nu_eleitoral for m in groups[0]}, {'DP00004', 'DP00005'})

	def test_unique_records_not_listed(self):
		resp = self.page()
		listed = {m.nu_eleitoral for g in resp.context['groups_nome'] + resp.context['groups_tel'] for m in g}
		self.assertNotIn('DP00006', listed)

	def test_clean_data_shows_success_notice(self):
		Membro.objects.all().delete()
		self.make('DP10001', nome='Sendiri Aja')
		resp = self.page()
		self.assertContains(resp, 'Laiha membru ho naran no data moris hanesan')
		self.assertContains(resp, "Laiha Nu. Telemovel ne'ebé uza dala barak")

	def test_roles(self):
		for u in ('presidente', 'koordpostu'):
			self.assertEqual(self.page(u).status_code, 200)
		for u in ('sekrpostu', 'sekrsuku', 'koordsuku', 'sekrorg', 'admin'):
			self.login(u)
			self.assertEqual(self.client.get(reverse('membro-dupla')).status_code, 403, u)

	def test_query_count_does_not_grow_with_number_of_groups(self):
		self.login('presidente')

		def count():
			with CaptureQueriesContext(connection) as ctx:
				self.client.get(reverse('membro-dupla'))
			return len(ctx)
		before = count()
		for i in range(15):  # 15 pasangan dobel baru
			dob = datetime.date(1970, 1, 1) + datetime.timedelta(days=i)
			self.make(f'DQ{i:04d}A', nome=f'Pasangan {i}', date_of_birth=dob)
			self.make(f'DQ{i:04d}B', self.vb, self.b1, nome=f'pasangan {i}', date_of_birth=dob)
		self.assertEqual(count(), before)


class DatabaseIntegrityTests(BaseCase):
	def test_expected_indexes_exist_in_database(self):
		with connection.cursor() as cursor:
			membro = connection.introspection.get_constraints(cursor, 'membro_membro')
			aloka = connection.introspection.get_constraints(cursor, 'membro_alokasaun')
			historia = connection.introspection.get_constraints(cursor, 'membro_historia')
			year = connection.introspection.get_constraints(cursor, 'custom_year')
		for name in ('membro_nome_dob_idx', 'membro_year_aprov_idx', 'membro_vil_aprov_idx', 'membro_ald_aprov_idx',
				'membro_org_aprov_idx', 'membro_dob_idx', 'membro_telefone_idx'):
			self.assertIn(name, membro)
		self.assertIn('aloka_ativu_niv_poz_idx', aloka)
		self.assertIn('historia_datetime_idx', historia)
		self.assertIn('historia_aksaun_idx', historia)
		self.assertTrue(any(c['columns'] == ['hashed'] and c['unique'] for c in membro.values()))
		self.assertTrue(any(c['columns'] == ['is_active'] and c['index'] for c in year.values()))

	def test_database_rejects_invalid_choices(self):
		m = self.make('DB00001')
		for field, bad in (('sex', 'X'), ('aprovasaun', 'Mungkin'), ('status', 'Entah')):
			with self.assertRaises(IntegrityError), transaction.atomic():
				Membro.objects.filter(pk=m.pk).update(**{field: bad})
		with self.assertRaises(IntegrityError), transaction.atomic():
			Alokasaun.objects.create(membro=m, nivel='Negara', pozisaun='Coordenador', data_hahu=datetime.date(2026, 1, 1))
		with self.assertRaises(IntegrityError), transaction.atomic():
			Alokasaun.objects.create(membro=m, nivel='Postu', pozisaun='Raja', data_hahu=datetime.date(2026, 1, 1))

	def test_hashed_is_unique(self):
		a, b = self.make('DB00002'), self.make('DB00003')
		with self.assertRaises(IntegrityError), transaction.atomic():
			Membro.objects.filter(pk=b.pk).update(hashed=a.hashed)

	def test_hashed_is_filled_for_all_hashed_models(self):
		self.assertEqual(len(self.make('DB00004').hashed), 64)
		self.assertEqual(len(Organizasaun.objects.create(code='XYZ', name='XYZ').hashed), 64)


class LoginThrottleTests(BaseCase):
	def setUp(self):
		cache.clear()
		self.addCleanup(cache.clear)

	def attempt(self, user='presidente', password='salah'):
		return self.client.post(reverse('login'), {'username': user, 'password': password})

	def test_blocks_after_five_failures_even_with_correct_password(self):
		for _ in range(5):
			self.assertEqual(self.attempt().status_code, 200)
		blocked = self.attempt(password='Teste-12345!')
		self.assertEqual(blocked.status_code, 429)
		self.assertContains(blocked, 'Tentativa gagal barak liu', status_code=429)
		self.assertNotIn('_auth_user_id', self.client.session)

	def test_other_username_is_not_affected(self):
		for _ in range(5):
			self.attempt('presidente')
		self.assertEqual(self.attempt('koordpostu', 'Teste-12345!').status_code, 302)

	def test_successful_login_resets_counter(self):
		for _ in range(4):
			self.attempt()
		self.assertEqual(self.attempt(password='Teste-12345!').status_code, 302)
		self.client.logout()
		for _ in range(4):
			self.assertEqual(self.attempt().status_code, 200)
		self.assertEqual(self.attempt(password='Teste-12345!').status_code, 302)

	def test_username_is_case_insensitive_for_throttling(self):
		for u in ('Presidente', 'PRESIDENTE', 'presidente', 'presidente ', 'PresiDente'):
			self.attempt(u)
		self.assertEqual(self.attempt('presidente', 'Teste-12345!').status_code, 429)

	def test_normal_error_message_still_shown_before_lock(self):
		self.assertContains(self.attempt(), 'Username ka password la loos.')


class HealthCheckTests(BaseCase):
	def test_ok_without_login_and_without_sensitive_data(self):
		resp = self.client.get('/healthz/')
		self.assertEqual(resp.status_code, 200)
		self.assertEqual(resp.json(), {'app': 'SGDM-PDPADA', 'status': 'ok', 'database': 'ok'})

	def test_reports_503_when_database_fails(self):
		with mock.patch('main.views.connection.cursor', side_effect=Exception('db mati')):
			resp = self.client.get('/healthz/')
		self.assertEqual(resp.status_code, 503)
		self.assertEqual(resp.json()['status'], 'error')
		self.assertNotIn('db mati', resp.content.decode())


@override_settings(PRIVATE_ROOT=PRIVATE_TMP)
class BackupCommandTests(TransactionTestCase):
	"""Tanpa transaksi pembungkus (TransactionTestCase): backup SQLite butuh koneksi tanpa transaksi terbuka."""

	def setUp(self):
		mun = Municipality.objects.create(name='Dili')
		post = AdministrativePost.objects.create(municipality=mun, name='Dom Aleixo')
		village = Village.objects.create(administrativepost=post, name='Suku A')
		self.aldeia = Aldeia.objects.create(village=village, name='A1')
		year = Year.objects.create(year=2026, is_active=True)
		Membro.objects.create(nome='Ana Cadangan', sex='Feto', date_of_birth=datetime.date(1990, 1, 1), nu_eleitoral='BK00001',
			village=village, aldeia=self.aldeia, year=year)
		for sub, name in (('foto', 'a.jpg'), ('eleitoral', 'b.pdf')):
			target = Path(PRIVATE_TMP) / sub
			target.mkdir(parents=True, exist_ok=True)
			(target / name).write_bytes(b'isi ' + name.encode())
		self.folder = tempfile.mkdtemp(prefix='pdpada-bk-')
		self.addCleanup(shutil.rmtree, self.folder, ignore_errors=True)
		self.addCleanup(shutil.rmtree, PRIVATE_TMP, ignore_errors=True)

	def run_backup(self, keep=14):
		out = io.StringIO()
		call_command('backup_data', dir=self.folder, keep=keep, stdout=out)
		return out.getvalue()

	def test_zip_contains_consistent_database_and_private_files(self):
		self.run_backup()
		files = list(Path(self.folder).glob('pdpada-*.zip'))
		self.assertEqual(len(files), 1)
		self.assertEqual(oct(files[0].stat().st_mode & 0o777), '0o600')
		with zipfile.ZipFile(files[0]) as z:
			names = z.namelist()
			self.assertIn('db.sqlite3', names)
			self.assertIn('private/foto/a.jpg', names)
			self.assertIn('private/eleitoral/b.pdf', names)
			self.assertIsNone(z.testzip())
			with tempfile.TemporaryDirectory() as tmp:
				z.extract('db.sqlite3', tmp)
				import sqlite3
				db = sqlite3.connect(Path(tmp) / 'db.sqlite3')
				self.assertEqual(db.execute("SELECT nome FROM membro_membro WHERE nu_eleitoral='BK00001'").fetchone()[0], 'Ana Cadangan')
				self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
				db.close()

	def test_rotation_keeps_only_newest(self):
		for stamp in ('20200101-000001', '20200101-000002', '20200101-000003'):
			(Path(self.folder) / f'pdpada-{stamp}.zip').write_bytes(b'x')
		self.run_backup(keep=2)
		names = sorted(p.name for p in Path(self.folder).glob('pdpada-*.zip'))
		self.assertEqual(len(names), 2)
		self.assertNotIn('pdpada-20200101-000001.zip', names)

	def test_refuses_non_sqlite_and_invalid_keep(self):
		with override_settings(DATABASES={'default': {'ENGINE': 'django.db.backends.mysql', 'NAME': 'x'}}):
			with self.assertRaises(CommandError):
				call_command('backup_data', stdout=io.StringIO())
		with self.assertRaises(CommandError):
			call_command('backup_data', keep=0, stdout=io.StringIO())

	def test_works_without_private_folder(self):
		shutil.rmtree(PRIVATE_TMP, ignore_errors=True)
		self.run_backup()
		with zipfile.ZipFile(next(Path(self.folder).glob('pdpada-*.zip'))) as z:
			self.assertEqual(z.namelist(), ['db.sqlite3'])


class BackupGuardTests(BaseCase):
	def test_refuses_to_run_inside_open_transaction(self):
		with self.assertRaises(CommandError) as ctx:
			call_command('backup_data', stdout=io.StringIO())
		self.assertIn('transaksi', str(ctx.exception))


class ProductionSettingsTests(BaseCase):
	def test_session_and_security_settings(self):
		self.assertEqual(settings.SESSION_COOKIE_AGE, 12 * 3600)
		self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
		self.assertEqual(settings.SECURE_REFERRER_POLICY, 'same-origin')
		self.assertTrue(settings.SECURE_CONTENT_TYPE_NOSNIFF)
		self.assertEqual(settings.SECURE_HSTS_SECONDS, 0)

	def test_logging_configured_for_application_logger(self):
		self.assertIn('pdpada', settings.LOGGING['loggers'])
		self.assertIn('console', settings.LOGGING['handlers'])


class FilterButtonsAndTablesTests(BaseCase):
	def setUp(self):
		self.make('FB00001', self.va, self.a1, sex='Mane', aprovasaun='Pendente')
		self.make('FB00002', self.va, self.a2, sex='Feto', aprovasaun='Pendente')
		self.make('FB00003', self.va, self.a1, sex='Mane', aprovasaun='Aprovadu')
		self.make('FB00004', self.vb, self.b1, sex='Mane', aprovasaun='Rejeitadu')

	def filters(self, user, query=''):
		self.login(user)
		resp = self.client.get(reverse('membro-list') + query)
		self.assertEqual(resp.status_code, 200)
		return resp, {f['label']: f for f in resp.context['filters']}

	# ---- daftar membru
	def test_member_list_has_coloured_buttons_with_counts(self):
		resp, f = self.filters('presidente')
		self.assertEqual({k: v['count'] for k, v in f.items()}, {'Hotu': 4, 'Pendente': 2, 'Aprovadu': 1, 'Rejeitadu': 1})
		self.assertContains(resp, 'class="btn-filter btn-filter-all active"')
		self.assertContains(resp, 'btn-filter-warn')
		self.assertContains(resp, 'btn-filter-ok')
		self.assertContains(resp, 'btn-filter-bad')
		self.assertContains(resp, '<span class="count">4</span>')

	def test_active_button_follows_query(self):
		for value in ('Pendente', 'Aprovadu', 'Rejeitadu'):
			resp, f = self.filters('presidente', f'?aprovasaun={value}')
			self.assertEqual([k for k, v in f.items() if v['active']], [value])
			listed = {m.aprovasaun for m in resp.context['objects']}
			self.assertEqual(listed, {value})

	def test_invalid_value_falls_back_to_hotu(self):
		_, f = self.filters('presidente', '?aprovasaun=bukan-status')
		self.assertEqual([k for k, v in f.items() if v['active']], ['Hotu'])

	def test_other_filters_are_kept_and_counted(self):
		_, f = self.filters('presidente', '?sex=Mane&aprovasaun=Pendente')
		self.assertEqual({k: v['count'] for k, v in f.items()}, {'Hotu': 3, 'Pendente': 1, 'Aprovadu': 1, 'Rejeitadu': 1})
		self.assertIn('sex=Mane', f['Aprovadu']['url'])
		self.assertIn('aprovasaun=Aprovadu', f['Aprovadu']['url'])
		self.assertNotIn('aprovasaun', f['Hotu']['url'])
		self.assertIn('sex=Mane', f['Hotu']['url'])

	def test_counts_respect_user_scope(self):
		_, f = self.filters('koordsuku')
		self.assertEqual({k: v['count'] for k, v in f.items()}, {'Hotu': 3, 'Pendente': 2, 'Aprovadu': 1, 'Rejeitadu': 0})

	def test_member_list_has_no_search_builder(self):
		self.login('presidente')
		resp = self.client.get(reverse('membro-list'))
		for needle in ('searchBuilder', 'SearchBuilder', 'Custom Search Builder', 'Add Condition', 'dtsb'):
			self.assertNotContains(resp, needle)
		self.assertContains(resp, 'datatable_defaults.js')

	# ---- historia
	def test_historia_buttons_with_counts_and_active_state(self):
		self.login('presidente')
		resp = self.client.get(reverse('historia-list'))
		f = {x['label']: x for x in resp.context['filters']}
		self.assertEqual(f['Hotu']['count'], Historia.objects.count())
		self.assertTrue(f['Hotu']['active'])
		self.assertTrue(all(x['kind'] in ('all', 'info', 'warn', 'ok', 'bad', 'dark') for x in f.values()))
		self.assertNotContains(resp, 'Custom Search Builder')
		self.assertContains(resp, 'btn-filter')

	def test_historia_filter_by_action_and_style(self):
		self.login('sekrsuku')
		self.client.post(reverse('membro-add'), self.form_data(nu='FB10001'))
		m = Membro.objects.get(nu_eleitoral='FB10001')
		self.login('presidente')
		self.client.post(reverse('aprovasaun-aprova', args=[m.hashed]))
		resp = self.client.get(reverse('historia-list'), {'aksaun': 'Aprova'})
		f = {x['label']: x for x in resp.context['filters']}
		self.assertTrue(f['Aprova']['active'])
		self.assertFalse(f['Hotu']['active'])
		self.assertEqual((f['Aprova']['icon'], f['Aprova']['kind']), ('fa-check-circle', 'ok'))
		self.assertEqual((f['Kria']['icon'], f['Kria']['kind']), ('fa-plus-circle', 'info'))
		self.assertEqual({h.aksaun for h in resp.context['objects']}, {'Aprova'})
		self.assertEqual(f['Aprova']['url'], '/membro/historia/?aksaun=Aprova')

	def test_historia_unknown_action_param_is_safe(self):
		self.login('presidente')
		resp = self.client.get(reverse('historia-list'), {'aksaun': '<script>x</script>'})
		self.assertEqual(resp.status_code, 200)
		self.assertNotContains(resp, '<script>x</script>')
		self.assertEqual(list(resp.context['objects']), [])

	def test_historia_action_with_space_in_name_links_correctly(self):
		Historia.objects.create(aksaun='Hare Dokumentu', membro_nome='x', user=self.users['presidente'])
		self.login('presidente')
		f = {x['label']: x for x in self.client.get(reverse('historia-list')).context['filters']}
		self.assertEqual(f['Hare Dokumentu']['url'], '/membro/historia/?aksaun=Hare+Dokumentu')
		resp = self.client.get(f['Hare Dokumentu']['url'])
		self.assertEqual([h.aksaun for h in resp.context['objects']], ['Hare Dokumentu'])

	# ---- tabel
	def test_search_builder_assets_removed(self):
		import os
		base = os.path.join(settings.BASE_DIR, 'main/static/main')
		for rel in ('datatables/js/dataTables.searchBuilder.min.js', 'datatables/js/searchBuilder.bootstrap4.min.js',
				'datatables/css/searchBuilder.bootstrap4.min.css'):
			self.assertFalse(os.path.exists(os.path.join(base, rel)), rel)
		init = open(os.path.join(base, 'js_custom/datatable_init.js')).read()
		self.assertNotIn('searchBuilder', init)
		for label in ('Excel', 'PDF', 'Imprime', 'Kolona'):
			self.assertIn(label, init)

	def test_tetun_texts_for_all_tables(self):
		import os
		path = os.path.join(settings.BASE_DIR, 'main/static/main/js_custom/datatable_defaults.js')
		text = open(path, encoding='utf-8').read()
		for needle in ('Buka:', 'Hatudu _MENU_ rejistu', "Laiha rejistu ne'ebé hetan", 'Tuir mai', 'Molok'):
			self.assertIn(needle, text)
		self.login('presidente')
		for name in ('membro-list', 'historia-list', 'aprovasaun-list', 'alokasaun-list'):
			resp = self.client.get(reverse(name))
			self.assertContains(resp, 'js_custom/datatable_defaults.js', msg_prefix=name)
			self.assertNotContains(resp, 'searchBuilder', msg_prefix=name)
		self.login('admin')
		for url in (reverse('user-list'), reverse('master-list', args=['suku'])):
			self.assertNotContains(self.client.get(url), 'searchBuilder')

	def test_defaults_script_loads_after_datatables_in_layout(self):
		self.login('presidente')
		html = self.client.get('/').content.decode()
		self.assertLess(html.index('jquery.dataTables.min.js'), html.index('datatable_defaults.js'))
