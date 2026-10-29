"""
tests.base — testlar uchun umumiy yordamchilar.

YGTestCase tez parol hasher'idan foydalanadi (standart PBKDF2 testlarni juda sekinlashtiradi).
"""
import datetime
import itertools
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.applications.models import Application
from apps.jobs.models import Category, Job
from apps.payments.models import Wallet
from apps.specializations.models import SpecializationRequest
from apps.users.models import User

FAST_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
PASSWORD = "Test-Pass-123!"
_numbers = itertools.count(1)


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class YGTestCase(TestCase):
    """Barcha loyiha testlari uchun asos."""


def make_user(role=User.Role.WORKER, **fields):
    number = next(_numbers)
    fields.setdefault("phone_number", f"+99890{number:07d}")
    fields.setdefault("first_name", f"Ism{number}")
    fields.setdefault("last_name", f"Familiya{number}")
    return User.objects.create_user(password=PASSWORD, role=role, **fields)


def make_category(spec=Category.SpecializationType.NONE, **fields):
    fields.setdefault("name", f"Kategoriya {next(_numbers)}")
    return Category.objects.create(required_specialization=spec, **fields)


def make_job(employer, category=None, **fields):
    defaults = {
        "title": "Uy tozalash",
        "description": "Ikki xonali uyni tozalash",
        "price": Decimal("100000.00"),
        "workers_needed": 1,
        "address": "Chilonzor 12-kvartal 5-uy, 45-xonadon",
        "area_label": "Chilonzor tumani",
        "latitude": Decimal("41.285000"),
        "longitude": Decimal("69.204000"),
        "work_date": timezone.localdate() + datetime.timedelta(days=1),
        "start_time": datetime.time(9, 0),
        "matching_mode": Job.MatchingMode.SELECTIVE,
    }
    defaults.update(fields)
    return Job.objects.create(employer=employer, category=category or make_category(), **defaults)


def approve_specialization(user, spec):
    return SpecializationRequest.objects.create(
        user=user, specialization_type=spec, status=SpecializationRequest.Status.APPROVED
    )


def fund(user, amount):
    wallet, _ = Wallet.objects.get_or_create(user=user)
    wallet.deposit(Decimal(amount))
    return wallet


def balance(user):
    wallet = Wallet.objects.filter(user=user).first()
    return wallet.balance if wallet else Decimal("0.00")


def make_application(job, worker, status=Application.Status.PENDING, unlocked=False):
    return Application.objects.create(
        job=job,
        worker=worker,
        status=status,
        is_unlocked=unlocked,
        unlocked_at=timezone.now() if unlocked else None,
    )


def set_commission(percent):
    """Testlar uchun aniq foiz (standart: ish beruvchi 5%, ishchi ishonch to'lovi 10%, ushlanadigan 5%)."""
    from apps.payments.models import PlatformSettings

    obj = PlatformSettings.get_solo()
    obj.commission_percent = Decimal(str(percent))
    obj.save()
    return obj
