from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse

from config import roles as R
from config.models import AuditLog
from config.testing import PASSWORD, WorldTestCase
from custom.models import Aldeia
from users.models import Profile


class RbacMatrixTests(WorldTestCase):
    def test_semua_papel_iha_grupu_ho_permisaun(self):
        from django.contrib.auth.models import Group
        for role, perms in R.ROLE_PERMISSIONS.items():
            g = Group.objects.get(name=role)
            have = {f'{p.content_type.app_label}.{p.codename}' for p in g.permissions.all()}
            self.assertEqual(have, set(perms), role)

    def test_aldeia_de_ite_bele_input_membru(self):
        for role, perms in R.ROLE_PERMISSIONS.items():
            self.assertEqual('membro.add_membru' in perms, role == R.ALDEIA, role)

    def test_password_hash_argon2(self):
        self.assertTrue(User.objects.get(username='admin1').password.startswith('argon2$'))


class LoginAxesTests(WorldTestCase):
    def test_login_loos(self):
        r = self.client.post(reverse('login'), {'username': 'ald1', 'password': PASSWORD})
        self.assertRedirects(r, reverse('home'), fetch_redirect_response=False)

    def test_bloku_depois_tentativa_sala(self):
        for _ in range(5):
            self.client.post(reverse('login'), {'username': 'ald1', 'password': 'sala-sala-sala'})
        # Mesmu password loos tuir ona bloku
        r = self.client.post(reverse('login'), {'username': 'ald1', 'password': PASSWORD})
        self.assertEqual(r.status_code, 429)
        self.assertTrue(AuditLog.objects.filter(action='locked_out').exists())

    def test_home_tenke_login(self):
        r = self.client.get(reverse('home'))
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login/', r['Location'])

    def test_logout_post_de_ite(self):
        self.login(self.u_ald1)
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertEqual(self.client.post(reverse('logout')).status_code, 302)

    def test_login_audit(self):
        self.client.post(reverse('login'), {'username': 'ald1', 'password': PASSWORD})
        self.assertTrue(AuditLog.objects.filter(action='login', username='ald1').exists())


class UserManagementSecurityTests(WorldTestCase):
    """Regresaun ba kerentanan audit: view jestaun user de'it @login_required."""
    def test_papel_la_admin_hetan_403(self):
        targets = [('user-list', {}), ('user-create', {}), ('user-edit', {'pk': self.u_admin.pk})]
        posts = [('user-reset-password', {'pk': self.u_admin.pk}), ('user-unlock', {'pk': self.u_admin.pk}),
                 ('user-toggle-active', {'pk': self.u_admin.pk})]
        for user in (self.u_ald1, self.u_suku1, self.u_postu1, self.u_pres, self.u_opd):
            self.login(user)
            for name, kw in targets:
                self.assertEqual(self.client.get(reverse(name, kwargs=kw)).status_code, 403, (user, name))
            for name, kw in posts:
                self.assertEqual(self.client.post(reverse(name, kwargs=kw)).status_code, 403, (user, name))

    def test_reset_password_ba_admin_la_bele_husi_aldeia(self):
        self.login(self.u_ald1)
        self.client.post(reverse('user-reset-password', kwargs={'pk': self.u_admin.pk}))
        self.u_admin.refresh_from_db()
        self.assertTrue(self.u_admin.check_password(PASSWORD))

    def test_admin_kria_user_ho_password_aleatoriu(self):
        self.login(self.u_admin)
        r = self.client.post(reverse('user-create'), {
            'username': 'ald9', 'first_name': 'Nono', 'role': R.ALDEIA, 'aldeia': self.a2.pk})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Cache-Control'], 'no-store')
        pwd = r.context['password']
        self.assertGreaterEqual(len(pwd), 12)
        u = User.objects.get(username='ald9')
        self.assertTrue(u.check_password(pwd))
        self.assertTrue(u.profile.must_change_password)
        self.assertEqual(list(u.groups.values_list('name', flat=True)), [R.ALDEIA])
        self.assertEqual(u.profile.aldeia, self.a2)

    def test_papel_territorial_tenke_eskopu(self):
        self.login(self.u_admin)
        r = self.client.post(reverse('user-create'), {
            'username': 'suku9', 'first_name': 'X', 'role': R.SUKU})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username='suku9').exists())

    def test_user_foun_obriga_troka_password(self):
        u = User.objects.create_user('novu', password=PASSWORD)
        Profile.objects.create(user=u)  # default must_change_password=True
        self.client.force_login(u)
        r = self.client.get(reverse('home'))
        self.assertRedirects(r, reverse('password_change'), fetch_redirect_response=False)
        r = self.client.post(reverse('password_change'), {
            'old_password': PASSWORD, 'new_password1': 'Foun-Passw0rd-Ultra-77', 'new_password2': 'Foun-Passw0rd-Ultra-77'})
        self.assertRedirects(r, reverse('home'), fetch_redirect_response=False)
        self.assertFalse(Profile.objects.get(user=u).must_change_password)

    def test_password_kráik_la_aseita(self):
        u = User.objects.create_user('novu2', password=PASSWORD)
        Profile.objects.create(user=u)
        self.client.force_login(u)
        r = self.client.post(reverse('password_change'), {
            'old_password': PASSWORD, 'new_password1': 'abc12345', 'new_password2': 'abc12345'})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(Profile.objects.get(user=u).must_change_password)

    def test_admin_la_bele_deativa_rasik(self):
        self.login(self.u_admin)
        self.client.post(reverse('user-toggle-active', kwargs={'pk': self.u_admin.pk}))
        self.u_admin.refresh_from_db()
        self.assertTrue(self.u_admin.is_active)

    def test_papel_determinístiku_ho_grupu_barak(self):
        from django.contrib.auth.models import Group
        from config.scope import get_role
        u = User.objects.create_user('multi', password=PASSWORD)
        u.groups.add(*Group.objects.filter(name__in=[R.ALDEIA, R.POSTU]))
        self.assertEqual(get_role(u), R.POSTU)  # prioridade as
