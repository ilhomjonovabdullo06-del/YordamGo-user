"""
apps.users — AppConfig signallarni ro'yxatdan o'tkazish uchun.
"""
from django.utils.translation import gettext_lazy as _
from django.apps import AppConfig


class UsersConfig(AppConfig):
    """users ilovasi konfiguratsiyasi."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.users"
    verbose_name = _("Foydalanuvchilar")

    def ready(self):
        """Ilova tayyor bo'lganda signallarni import qilish."""
        import apps.users.signals  # noqa: F401
