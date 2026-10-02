from django.db import IntegrityError, transaction
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from config import roles as R
from config.models import AuditLog
from config.testing import PASSWORD, WorldTestCase
from custom.models import Aldeia
from membro.models import Kargu, Membru

NEW = {'nu_eleitoral': 'ab-100', 'naran': 'Foun', 'fatin_moris': 'Dili', 'data_moris': '1995-01-01',
       'sexu': 'M', 'estadu_civil': '', 'edukasaun': '', 'okupasaun': '', 'telemovel': '', 'email': '',
       'enderesu': ''}


class ScopeVisibilityTests(WorldTestCase):
    def names(self, user):
        self.login(user)
        r = self.client.get(reverse('membru-list'))
        self.assertEqual(r.status_code, 200)
        return {m.naran for m in r.context['membrus']}

    def test_eskopu_per_papel(self):
        self.assertEqual(self.names(self.u_ald1), {'Ana'})
        self.assertEqual(self.names(self.u_suku1), {'Ana', 'Bino'})
        self.assertEqual(self.names(self.u_postu1), {'Ana', 'Bino', 'Carla'})
        self.assertEqual(self.names(self.u_pres), {'Ana', 'Bino', 'Carla', 'Dino'})
        self.assertEqual(self.names(self.u_admin), {'Ana', 'Bino', 'Carla', 'Dino'})
        self.assertEqual(self.names(self.u_opd), {'Ana'})  # de'it membru organizasaun OPD

    def test_idor_detallu_edita_foto_hamoos_404(self):
        # Aldeia A1 koko aksesu membru A2/A3/A4 liu husi UUID
        self.login(self.u_ald1)
        for m in (self.m2, self.m3, self.m4):
            for name in ('membru-detail', 'membru-edit', 'membru-foto'):
                r = self.client.get(reverse(name, kwargs={'public_id': m.public_id}))
                self.assertEqual(r.status_code, 404, (m, name))
        # Suku S1 la bele haree A3 (Suku seluk)
        self.login(self.u_suku1)
        self.assertEqual(self.client.get(reverse('membru-detail', kwargs={'public_id': self.m3.public_id})).status_code, 404)

    def test_url_pk_la_uza_id_sequénsial(self):
        self.assertNotEqual(str(self.m1.public_id), str(self.m1.pk))
        self.assertEqual(len(str(self.m1.public_id)), 36)

    def test_media_la_publiku(self):
        self.assertEqual(self.client.get('/media/membru/x.jpg').status_code, 404)

    def test_foto_view_tenke_login(self):
        r = self.client.get(reverse('membru-foto', kwargs={'public_id': self.m1.public_id}))
        self.assertEqual(r.status_code, 302)


class InputRulesTests(WorldTestCase):
    def test_aldeia_de_ite_input(self):
        for user in (self.u_admin, self.u_pres, self.u_postu1, self.u_suku1, self.u_opd):
            self.login(user)
            self.assertEqual(self.client.get(reverse('membru-create')).status_code, 403, user)
            self.assertEqual(self.client.post(reverse('membru-create'), NEW).status_code, 403, user)
        self.assertFalse(Membru.objects.filter(nu_eleitoral='AB-100').exists())

    def test_aldeia_input_aldeia_automátiku(self):
        self.login(self.u_ald1)
        data = dict(NEW, aldeia=self.a3.pk)  # koko forja aldeia seluk
        r = self.client.post(reverse('membru-create'), data)
        self.assertEqual(r.status_code, 302)
        m = Membru.objects.get(nu_eleitoral='AB-100')
        self.assertEqual(m.aldeia, self.a1)
        self.assertEqual(m.estadu, Membru.Estadu.REJISTADU)
        self.assertEqual(m.created_by, self.u_ald1)
        self.assertTrue(AuditLog.objects.filter(action='membru_create').exists())

    def test_nu_eleitoral_úniku(self):
        self.login(self.u_ald1)
        r = self.client.post(reverse('membru-create'), dict(NEW, nu_eleitoral='0003'))
        self.assertEqual(r.status_code, 200)
        self.assertIn('nu_eleitoral', r.context['form'].errors)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.make_membru('0001', 'Dobru', self.a1, self.u_ald1)

    def test_idade_minimu(self):
        self.login(self.u_ald1)
        r = self.client.post(reverse('membru-create'), dict(NEW, data_moris='2020-01-01'))
        self.assertEqual(r.status_code, 200)
        self.assertIn('data_moris', r.context['form'].errors)

    def test_edita_de_ite_molok_konfirma(self):
        self.login(self.u_ald1)
        url = reverse('membru-edit', kwargs={'public_id': self.m1.public_id})
        self.assertEqual(self.client.get(url).status_code, 200)
        self.m1.konfirma(self.u_suku1)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_suku_la_bele_edita(self):
        self.login(self.u_suku1)
        r = self.client.get(reverse('membru-edit', kwargs={'public_id': self.m1.public_id}))
        self.assertEqual(r.status_code, 403)


class WorkflowTests(WorldTestCase):
    def post(self, user, name, m):
        self.login(user)
        return self.client.post(reverse(name, kwargs={'public_id': m.public_id}))

    def test_fluxu_aldeia_suku_postu(self):
        # Postu la bele aprova molok Suku konfirma
        self.post(self.u_postu1, 'membru-aprova', self.m1)
        self.m1.refresh_from_db()
        self.assertEqual(self.m1.estadu, Membru.Estadu.REJISTADU)
        self.post(self.u_suku1, 'membru-konfirma', self.m1)
        self.m1.refresh_from_db()
        self.assertEqual((self.m1.estadu, self.m1.konfirma_by), (Membru.Estadu.KONFIRMADU, self.u_suku1))
        self.post(self.u_postu1, 'membru-aprova', self.m1)
        self.m1.refresh_from_db()
        self.assertEqual((self.m1.estadu, self.m1.aprova_by), (Membru.Estadu.APROVADU, self.u_postu1))

    def test_suku_la_bele_konfirma_membru_suku_seluk(self):
        r = self.post(self.u_suku1, 'membru-konfirma', self.m3)
        self.assertEqual(r.status_code, 404)
        self.m3.refresh_from_db()
        self.assertEqual(self.m3.estadu, Membru.Estadu.REJISTADU)

    def test_aldeia_la_bele_konfirma_ka_aprova(self):
        self.assertEqual(self.post(self.u_ald1, 'membru-konfirma', self.m1).status_code, 403)
        self.assertEqual(self.post(self.u_ald1, 'membru-aprova', self.m1).status_code, 403)

    def test_konfirma_tenke_post(self):
        self.login(self.u_suku1)
        r = self.client.get(reverse('membru-konfirma', kwargs={'public_id': self.m1.public_id}))
        self.assertEqual(r.status_code, 405)

    def test_hamoos_soft_de_ite_admin(self):
        self.assertEqual(self.post(self.u_ald1, 'membru-delete', self.m1).status_code, 403)
        self.assertEqual(self.post(self.u_admin, 'membru-delete', self.m1).status_code, 302)
        self.assertFalse(Membru.objects.filter(pk=self.m1.pk).exists())
        self.assertTrue(Membru.all_objects.filter(pk=self.m1.pk, deleted_by=self.u_admin).exists())
        # Nu. eleitoral bele uza fali depois hamoos
        self.make_membru('0001', 'Foun', self.a1, self.u_ald1)


class KarguTests(WorldTestCase):
    def kargu(self, **kw):
        base = dict(membru=self.m1, tipu='coordenador', nivel='aldeia', aldeia=self.a1)
        base.update(kw)
        k = Kargu(**base)
        k.full_clean()
        k.save()
        return k

    def test_koordenador_no_sekjen_ida_ba_wilayah(self):
        self.kargu()
        self.kargu(tipu='sekjen', membru=self.m1)  # sekjen ho koordenador diferente tipu: OK
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self.kargu(membru=self.m1)  # koordenador daruak ba aldeia hanesan

    def test_kargu_remata_loke_fatin(self):
        k = self.kargu()
        k.is_active = False
        k.save()
        self.kargu()  # bele ho ema foun

    def test_nivel_no_wilayah_tenke_hanesan(self):
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self.kargu(nivel='suku', aldeia=self.a1, village=None)
        with self.assertRaises(ValidationError):
            self.kargu(nivel='aldeia', aldeia=self.a1, village=self.s1)

    def test_membru_tenke_hela_iha_wilayah(self):
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self.kargu(membru=self.m3, aldeia=self.a1)  # Carla hela iha A3
        self.kargu(membru=self.m2, nivel='suku', aldeia=None, village=self.s1)  # Bino iha S1: OK

    def test_db_check_constraint(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Kargu.objects.create(membru=self.m1, tipu='sekjen', nivel='aldeia', aldeia=None)

    def test_kargu_eskopu(self):
        self.kargu()
        self.kargu(membru=self.m3, nivel='aldeia', aldeia=self.a3)
        self.login(self.u_ald1)
        r = self.client.get(reverse('kargu-list'))
        self.assertEqual([k.membru.naran for k in r.context['kargus']], ['Ana'])
        self.login(self.u_postu1)
        self.assertEqual(len(r := self.client.get(reverse('kargu-list')).context['kargus']), 2)

    def test_admin_de_ite_kria_kargu(self):
        self.login(self.u_postu1)
        self.assertEqual(self.client.get(reverse('kargu-create')).status_code, 403)
        self.login(self.u_admin)
        r = self.client.post(reverse('kargu-create'), {
            'membru': self.m1.pk, 'tipu': 'coordenador', 'nivel': 'aldeia', 'aldeia': self.a1.pk})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Kargu.objects.count(), 1)


class ReportApiTests(WorldTestCase):
    def test_api_tenke_login(self):
        self.assertEqual(APIClient().get(reverse('api-membru-sumariu')).status_code, 403)

    def test_api_la_aseita_basic_auth(self):
        import base64
        c = APIClient(enforce_csrf_checks=True)
        c.credentials(HTTP_AUTHORIZATION='Basic ' + base64.b64encode(f'admin1:{PASSWORD}'.encode()).decode())
        self.assertEqual(c.get(reverse('api-membru-sumariu')).status_code, 403)

    def test_api_eskopu(self):
        self.login(self.u_suku1)
        d = self.client.get(reverse('api-membru-sumariu')).json()
        self.assertEqual(d['group_label'], 'Aldeia')
        self.assertEqual(d['label'], ['A1', 'A2'])
        self.login(self.u_pres)
        d = self.client.get(reverse('api-membru-sumariu')).json()
        self.assertEqual(d['group_label'], 'Munisípiu')
        self.assertEqual(sum(d['mane']) + sum(d['feto']), 4)

    def test_dashboard_papel_hotu(self):
        for u in (self.u_admin, self.u_pres, self.u_postu1, self.u_suku1, self.u_ald1, self.u_opd):
            self.login(u)
            self.assertEqual(self.client.get(reverse('report-dash')).status_code, 200, u)
            self.assertEqual(self.client.get(reverse('home')).status_code, 200, u)
