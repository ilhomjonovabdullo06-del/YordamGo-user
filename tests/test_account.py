"""
tests.test_account — parol va telefon raqamni o'zgartirish: parol bilan tasdiqlash, noyoblik, sessiya, limit.
"""
from django.core.cache import cache
from django.urls import reverse

from apps.users.models import User

from .base import PASSWORD, YGTestCase, make_user


class ChangePasswordTest(YGTestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user()
        self.client.force_login(self.user)
        self.url = reverse("users:change-password")

    def post(self, old=PASSWORD, new="Yangi-Parol-2026!", confirm=None):
        return self.client.post(self.url, {"old_password": old, "new_password1": new, "new_password2": confirm or new})

    def test_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_changes_password_and_keeps_session(self):
        response = self.post()
        self.assertRedirects(response, reverse("users:profile"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Yangi-Parol-2026!"))
        self.assertEqual(self.client.get(reverse("users:profile")).status_code, 200)  # hali kirgan
        self.client.logout()
        self.assertTrue(self.client.login(phone_number=self.user.phone_number, password="Yangi-Parol-2026!"))

    def test_wrong_old_password_and_weak_new_password_rejected(self):
        self.assertContains(self.post(old="noto'g'ri"), "errorlist")
        self.assertContains(self.post(new="12345678"), "errorlist")
        self.assertContains(self.post(confirm="boshqa"), "errorlist")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_old_password_guessing_is_limited(self):
        for _ in range(5):
            self.post(old="noto'g'ri")
        response = self.post(old=PASSWORD)  # to'g'ri parol ham bloklanadi
        self.assertContains(response, "errorlist")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))


class ChangePhoneTest(YGTestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user()
        self.client.force_login(self.user)
        self.url = reverse("users:change-phone")

    def post(self, phone, password=PASSWORD):
        return self.client.post(self.url, {"new_phone": phone, "password": password})

    def test_changes_phone_with_any_format_and_login_uses_new_number(self):
        response = self.post("90 555 44 33")
        self.assertRedirects(response, reverse("users:profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone_number, "+998905554433")
        self.client.logout()
        self.assertTrue(self.client.login(phone_number="+998905554433", password=PASSWORD))
        self.assertFalse(self.client.login(phone_number="+998900000001", password=PASSWORD))

    def test_wrong_password_duplicate_and_invalid_rejected(self):
        old = self.user.phone_number
        other = make_user()
        for phone, password in (("90 555 44 33", "xato"), (other.phone_number, PASSWORD), ("123", PASSWORD), (old, PASSWORD)):
            self.assertContains(self.post(phone, password), "errorlist")
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone_number, old)

    def test_password_guessing_is_limited(self):
        for _ in range(5):
            self.post("90 555 44 33", "xato")
        self.assertContains(self.post("90 555 44 33", PASSWORD), "errorlist")
        self.assertFalse(User.objects.filter(phone_number="+998905554433").exists())

    def test_profile_links_to_both(self):
        page = self.client.get(reverse("users:profile"))
        self.assertContains(page, self.url)
        self.assertContains(page, reverse("users:change-password"))
