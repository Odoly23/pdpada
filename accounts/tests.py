from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import AuditLog

from .models import User


class LoginTests(TestCase):
    def setUp(self):
        cache.clear()
        User.objects.create_user("rita", password="S3gredu!pass")

    def test_login_ok_and_audited(self):
        r = self.client.post(reverse("accounts:login"), {"username": "rita", "password": "S3gredu!pass"})
        self.assertRedirects(r, reverse("core:dashboard"), fetch_redirect_response=False)
        self.assertTrue(AuditLog.objects.filter(action="login", username="rita").exists())

    def test_locks_after_five_failures(self):
        for _ in range(5):
            self.client.post(reverse("accounts:login"), {"username": "rita", "password": "bad"})
        # Even the correct password is refused while locked.
        r = self.client.post(reverse("accounts:login"), {"username": "rita", "password": "S3gredu!pass"})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertTrue(AuditLog.objects.filter(action="login_locked").exists())

    def test_dashboard_requires_login(self):
        r = self.client.get(reverse("core:dashboard"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("accounts:login"), r["Location"])


class LandingTests(TestCase):
    def test_public_and_default_tetun(self):
        r = self.client.get(reverse("core:landing"))
        self.assertContains(r, "Horáriu Ró-Laran")

    def test_language_switch(self):
        r = self.client.post("/i18n/setlang/", {"language": "en", "next": "/"}, follow=True)
        self.assertContains(r, "Ferry Schedule")
