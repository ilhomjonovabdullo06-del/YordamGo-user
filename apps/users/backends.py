"""
apps.users.backends — telefon raqam bilan autentifikatsiya.

Raqam har qanday yozilishda (+998..., 998..., 90 123 45 67) bir xil ko'rinishga keltiriladi,
xato urinishlar cheklanadi (apps/users/throttle.py). Sayt login formasi, /admin/ va boshqa
barcha authenticate() chaqiruvlari shu yerdan o'tadi.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from . import throttle
from .phone import normalize_phone


class PhoneNumberBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        raw = kwargs.get(get_user_model().USERNAME_FIELD, username)
        if raw is None or password is None:
            return None
        # Tanib bo'lmaydigan eski yozuvlar uchun asl qiymat bilan ham urinib ko'riladi
        phone = normalize_phone(raw) or str(raw).strip()
        if throttle.is_locked(request, phone):
            return None
        user = super().authenticate(request, username=phone, password=password)
        if user is None:
            throttle.register_failure(request, phone)
        else:
            throttle.reset(phone)
        return user
