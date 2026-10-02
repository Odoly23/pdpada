"""Fixture bersama ba tes: wilayah, papel no user."""
from django.contrib.auth.models import Group, User
from django.test import TestCase

from config import roles as R
from custom.models import AdministrativePost, Aldeia, Municipality, Village
from membro.models import Membru, Organizasaun
from users.models import Profile
from users.rbac import sync_groups

PASSWORD = 'Tes-Passw0rd-Kuat-123!'


class WorldTestCase(TestCase):
    """
    Dili → Postu P1 { Suku S1 {A1, A2}, Suku S2 {A3} }, Postu P2 { Suku S3 {A4} }
    """
    @classmethod
    def setUpTestData(cls):
        sync_groups()
        cls.mun = Municipality.objects.create(code='DL', name='Dili')
        cls.p1 = AdministrativePost.objects.create(municipality=cls.mun, name='P1')
        cls.p2 = AdministrativePost.objects.create(municipality=cls.mun, name='P2')
        cls.s1 = Village.objects.create(administrativepost=cls.p1, name='S1')
        cls.s2 = Village.objects.create(administrativepost=cls.p1, name='S2')
        cls.s3 = Village.objects.create(administrativepost=cls.p2, name='S3')
        cls.a1 = Aldeia.objects.create(village=cls.s1, name='A1')
        cls.a2 = Aldeia.objects.create(village=cls.s1, name='A2')
        cls.a3 = Aldeia.objects.create(village=cls.s2, name='A3')
        cls.a4 = Aldeia.objects.create(village=cls.s3, name='A4')
        cls.opd = Organizasaun.objects.create(code='OPD', name='Organizasaun Pemuda')
        cls.omd = Organizasaun.objects.create(code='OMD', name='Organizasaun Mulher')

        cls.u_admin = cls.make_user('admin1', R.ADMIN)
        cls.u_pres = cls.make_user('pres1', R.PRESIDENTE)
        cls.u_postu1 = cls.make_user('postu1', R.POSTU, postu=cls.p1)
        cls.u_suku1 = cls.make_user('suku1', R.SUKU, village=cls.s1)
        cls.u_ald1 = cls.make_user('ald1', R.ALDEIA, aldeia=cls.a1)
        cls.u_ald3 = cls.make_user('ald3', R.ALDEIA, aldeia=cls.a3)
        cls.u_opd = cls.make_user('opd1', R.OPD, organizasaun=cls.opd)

        cls.m1 = cls.make_membru('0001', 'Ana', cls.a1, cls.u_ald1)
        cls.m2 = cls.make_membru('0002', 'Bino', cls.a2, cls.u_ald1)
        cls.m3 = cls.make_membru('0003', 'Carla', cls.a3, cls.u_ald3, sexu='F')
        cls.m4 = cls.make_membru('0004', 'Dino', cls.a4, cls.u_admin)
        cls.m1.organizasaun.add(cls.opd)

    @classmethod
    def make_user(cls, username, role, **scope):
        u = User.objects.create_user(username, password=PASSWORD)
        u.groups.add(Group.objects.get(name=role))
        Profile.objects.create(user=u, must_change_password=False, **scope)
        return u

    @classmethod
    def make_membru(cls, nu, naran, aldeia, by, sexu='M', **kw):
        return Membru.objects.create(nu_eleitoral=nu, naran=naran, data_moris='1990-05-05', sexu=sexu,
                                     aldeia=aldeia, created_by=by, **kw)

    def login(self, user):
        self.client.logout()
        self.client.force_login(user)
