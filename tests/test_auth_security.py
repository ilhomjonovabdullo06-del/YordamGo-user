"""
tests.test_auth_security — telefon normallashtirish, login limiti, bloklash, DRF (audit #11, #12, C8).
"""
import base64
import importlib
import os
import sys
from unittest import mock

from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from rest_framework.test import APIClient

from apps.users.models import User
from apps.users.phone import format_phone, mask_phone, normalize_phone

from .base import PASSWORD, YGTestCase, make_user


class PhoneFormatTest(YGTestCase):
    def test_normalize_variants(self):
        for raw in ("901234567", "90 123 45 67", "+998 (90) 123-45-67", "998901234567", "00998901234567"):
            self.assertEqual(normalize_phone(raw), "+998901234567", raw)
        for raw in ("", "12345", "+7 901 234 5678", "abc"):
            self.assertIsNone(normalize_phone(raw), raw)

    def test_format_and_mask(self):
        self.assertEqual(format_phone("901234567"), "+998 90 123 45 67")
        self.assertEqual(mask_phone("+998901234567"), "+998 90 *** ** 67")

    def test_manager_normalizes_and_rejects_invalid(self):
        user = User.objects.create_user(phone_number="93 111 22 33", password=PASSWORD)
        self.assertEqual(user.phone_number, "+998931112233")
        with self.assertRaises(ValueError):
            User.objects.create_user(phone_number="12345", password=PASSWORD)


class RegistrationLoginTest(YGTestCase):
    def setUp(self):
        cache.clear()

    def register(self, phone):
        return self.client.post(reverse("users:register"), {
            "first_name": "Ali", "last_name": "Valiyev", "phone_number": phone, "role": "worker",
            "password1": "Murakkab-Parol-2026", "password2": "Murakkab-Parol-2026",
        })

    def test_register_normalizes_and_blocks_duplicates_across_formats(self):
        self.register("90 555 66 77")
        self.assertTrue(User.objects.filter(phone_number="+998905556677").exists())
        self.client.logout()
        response = self.register("+998905556677")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(phone_number="+998905556677").count(), 1)

    def test_login_with_any_format(self):
        make_user(phone_number="+998907770011")
        response = self.client.post(reverse("users:login"), {"phone_number": "90 777 00 11", "password": PASSWORD})
        self.assertEqual(response.status_code, 302)

    def test_bruteforce_lockout(self):
        make_user(phone_number="+998907770022")
        for _ in range(5):
            self.client.post(reverse("users:login"), {"phone_number": "907770022", "password": "noto'g'ri"})
        response = self.client.post(reverse("users:login"), {"phone_number": "907770022", "password": PASSWORD})
        self.assertEqual(response.status_code, 200)  # to'g'ri parol ham vaqtincha qabul qilinmaydi
        self.assertContains(response, "15 daqiqadan keyin")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_success_resets_phone_counter(self):
        make_user(phone_number="+998907770033")
        for _ in range(4):
            self.client.post(reverse("users:login"), {"phone_number": "907770033", "password": "xato"})
        self.client.post(reverse("users:login"), {"phone_number": "907770033", "password": PASSWORD})
        self.client.logout()
        for _ in range(4):
            self.client.post(reverse("users:login"), {"phone_number": "907770033", "password": "xato"})
        response = self.client.post(reverse("users:login"), {"phone_number": "907770033", "password": PASSWORD})
        self.assertEqual(response.status_code, 302)

    def test_blocked_user_session_is_terminated(self):
        user = make_user()
        self.client.force_login(user)
        User.objects.filter(pk=user.pk).update(is_blocked=True)
        response = self.client.get(reverse("payments:wallet_detail"))
        self.assertRedirects(response, reverse("users:login"), fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)


class ApiSecurityTest(YGTestCase):
    def setUp(self):
        cache.clear()
        self.api = APIClient()
        self.user = make_user(phone_number="+998907770044")

    def test_basic_auth_not_accepted(self):
        token = base64.b64encode(f"+998907770044:{PASSWORD}".encode()).decode()
        response = self.api.get("/api/users/profile/", HTTP_AUTHORIZATION=f"Basic {token}")
        self.assertEqual(response.status_code, 403)

    def test_phone_is_read_only_and_role_switch_creates_profile(self):
        self.api.force_authenticate(self.user)
        response = self.api.patch("/api/users/profile/", {"phone_number": "+998909999999", "role": "employer"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone_number, "+998907770044")
        self.assertTrue(hasattr(self.user, "employer_profile"))
        # Profil tahriri ham ishlaydi (avval profil yo'qligidan 500 bo'lardi)
        self.client.force_login(self.user)
        response = self.client.post(reverse("users:profile-edit"), {"first_name": "A", "last_name": "B", "company_name": ""})
        self.assertEqual(response.status_code, 302)

    def test_register_api_normalizes_phone(self):
        response = self.api.post("/api/users/register/", {
            "phone_number": "90 777 00 55", "first_name": "A", "last_name": "B", "role": "worker",
            "password": "Murakkab-Parol-2026", "password2": "Murakkab-Parol-2026",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["user"]["phone_number"], "+998907770055")


class ProdSettingsTest(YGTestCase):
    def import_prod(self, env):
        sys.modules.pop("config.settings.prod", None)
        with mock.patch.dict(os.environ, env, clear=False):
            if "SECRET_KEY" not in env:
                os.environ.pop("SECRET_KEY", None)
            return importlib.import_module("config.settings.prod")

    def tearDown(self):
        sys.modules.pop("config.settings.prod", None)

    ENV = {"ALLOWED_HOSTS": "yordamgo.example", "DATABASE_URL": "postgres://u:p@localhost:5432/db"}

    def test_secret_key_required(self):
        from decouple import UndefinedValueError
        with self.assertRaises(UndefinedValueError):
            self.import_prod(dict(self.ENV))
        with self.assertRaises(ImproperlyConfigured):
            self.import_prod({**self.ENV, "SECRET_KEY": "unsafe-secret-key-change-in-production"})
        module = self.import_prod({**self.ENV, "SECRET_KEY": "x" * 50})
        self.assertFalse(module.ALLOW_TEST_DEPOSIT)
        self.assertFalse(module.DEBUG)

    def test_hosts_and_database_required(self):
        env = {"SECRET_KEY": "x" * 50}
        with self.assertRaises(ImproperlyConfigured):
            self.import_prod({**env, "ALLOWED_HOSTS": "", "DATABASE_URL": self.ENV["DATABASE_URL"], "RENDER_EXTERNAL_HOSTNAME": ""})
        with self.assertRaises(ImproperlyConfigured):
            self.import_prod({**env, "ALLOWED_HOSTS": "a.example", "DATABASE_URL": ""})

    def test_production_security_settings(self):
        module = self.import_prod({**self.ENV, "SECRET_KEY": "x" * 50, "RENDER_EXTERNAL_HOSTNAME": "app.onrender.com"})
        self.assertIn("app.onrender.com", module.ALLOWED_HOSTS)
        self.assertIn("https://app.onrender.com", module.CSRF_TRUSTED_ORIGINS)
        self.assertTrue(module.SECURE_SSL_REDIRECT)
        self.assertTrue(module.SESSION_COOKIE_SECURE and module.CSRF_COOKIE_SECURE)
        self.assertGreaterEqual(module.SECURE_HSTS_SECONDS, 31536000)
        self.assertTrue(module.USE_X_FORWARDED_FOR)
        self.assertEqual(module.DATABASES["default"]["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(module.SECURE_REFERRER_POLICY, "strict-origin-when-cross-origin")  # OSM plitkalari
        self.assertIn("whitenoise.middleware.WhiteNoiseMiddleware", module.MIDDLEWARE)
        from config.settings import base
        self.assertNotIn("whitenoise.middleware.WhiteNoiseMiddleware", base.MIDDLEWARE)
        self.assertNotEqual(module.STORAGES["staticfiles"]["BACKEND"], "django.contrib.staticfiles.storage.StaticFilesStorage")
