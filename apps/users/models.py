"""
apps.users.models — YordamGo foydalanuvchilar modellari.

Modellar:
    User            — AbstractUser asosida custom foydalanuvchi modeli
    WorkerProfile   — Ishchi profili (User bilan OneToOne)
    EmployerProfile — Ish beruvchi profili (User bilan OneToOne)
"""
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from .phone import normalize_phone


class UserManager(BaseUserManager):
    """
    Custom UserManager — login maydoni sifatida phone_number ishlatiladi.
    """

    def create_user(self, phone_number, password=None, **extra_fields):
        """Oddiy foydalanuvchi yaratish."""
        if not phone_number:
            raise ValueError("Telefon raqam majburiy.")
        normalized = normalize_phone(phone_number)
        if normalized is None:
            raise ValueError("Telefon raqam noto'g'ri. Namuna: +998901234567")
        phone_number = normalized
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        """Superuser yaratish."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.WORKER)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser uchun is_staff=True bo'lishi kerak.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser uchun is_superuser=True bo'lishi kerak.")

        return self.create_user(phone_number, password, **extra_fields)


class User(AbstractUser):
    """
    YordamGo platformasining asosiy foydalanuvchi modeli.

    AbstractUser dan meros oladi, username maydoni o'chiriladi,
    telefon raqam asosiy identifikator va login maydoni sifatida ishlatiladi.

    Maydonlar:
        phone_number  — unikal telefon raqam (login uchun)
        role          — faol rejim: 'worker' yoki 'employer'
        is_verified   — ID tasdiqlash holati (hozircha faqat maydon)
        created_at    — yaratilgan vaqt
    """

    class Role(models.TextChoices):
        WORKER = "worker", _("Ishchi")
        EMPLOYER = "employer", _("Ish beruvchi")

    # username maydonini o'chiramiz, phone_number bilan almashtiramiz
    username = None

    # Doim +998XXXXXXXXX ko'rinishida saqlanadi (apps/users/phone.py, UserManager, formalar)
    phone_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_("Telefon raqam"),
        help_text=_("+998901234567 formatida kiriting"),
    )
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.WORKER,
        verbose_name=_("Rol (faol rejim)"),
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name=_("Tasdiqlangan"),
        help_text=_("Foydalanuvchi hujjatlari tekshirilganmi"),
    )
    is_blocked = models.BooleanField(
        default=False,
        verbose_name=_("Bloklangan"),
        help_text=_("True bo'lsa, foydalanuvchi tizimga kira olmaydi"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Yaratilgan vaqt"))

    # Login maydoni sifatida phone_number ishlatiladi
    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    class Meta:
        verbose_name = _("Foydalanuvchi")
        verbose_name_plural = _("Foydalanuvchilar")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_full_name()} ({self.phone_number})"

    @property
    def is_worker(self):
        """Foydalanuvchi ishchi rejimidami."""
        return self.role == self.Role.WORKER

    @property
    def is_employer(self):
        """Foydalanuvchi ish beruvchi rejimidami."""
        return self.role == self.Role.EMPLOYER

    def ensure_profile(self):
        """Joriy rol uchun profil (rol almashganda yo'q bo'lishi mumkin — shunda yaratiladi)."""
        if self.is_worker:
            return WorkerProfile.objects.get_or_create(user=self)[0]
        return EmployerProfile.objects.get_or_create(user=self)[0]


class WorkerProfile(models.Model):
    """
    Ishchi foydalanuvchi profili.

    User modeli bilan OneToOne bog'langan.
    Kelajakda 'skills' maydoni 'jobs' moduli bilan ForeignKey'ga aylantiriladi.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="worker_profile",
        verbose_name=_("Foydalanuvchi"),
    )
    skills = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Ko'nikmalar"),
        help_text=_("Ko'nikmalar ro'yxati (JSON). Kelajakda kategoriyalarga bog'lanadi."),
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        verbose_name=_("Reyting"),
    )
    completed_jobs_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Bajarilgan ishlar soni"),
    )
    bio = models.TextField(
        blank=True,
        verbose_name=_("O'zi haqida"),
        help_text=_("Qisqa tarjimayi hol yoki o'zini tanishtirish"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Yaratilgan vaqt"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Yangilangan vaqt"))

    class Meta:
        verbose_name = _("Ishchi profili")
        verbose_name_plural = _("Ishchi profillari")

    def __str__(self):
        return f"Ishchi: {self.user.get_full_name()} ({self.user.phone_number})"


class EmployerProfile(models.Model):
    """
    Ish beruvchi foydalanuvchi profili.

    User modeli bilan OneToOne bog'langan.
    Jismoniy shaxslar uchun company_name ixtiyoriy.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="employer_profile",
        verbose_name=_("Foydalanuvchi"),
    )
    company_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("Kompaniya nomi"),
        help_text=_("Jismoniy shaxs bo'lsa bo'sh qoldiring"),
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        verbose_name=_("Reyting"),
    )
    posted_jobs_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_("E'lon qilingan ishlar soni"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Yaratilgan vaqt"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Yangilangan vaqt"))

    class Meta:
        verbose_name = _("Ish beruvchi profili")
        verbose_name_plural = _("Ish beruvchi profillari")

    def __str__(self):
        name = self.company_name or self.user.get_full_name()
        return f"Ish beruvchi: {name} ({self.user.phone_number})"
