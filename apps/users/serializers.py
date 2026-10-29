"""
apps.users.serializers — DRF serializer'lar.

Serializer'lar:
    UserSerializer          — Foydalanuvchi ma'lumotlari
    WorkerProfileSerializer — Ishchi profili
    EmployerProfileSerializer — Ish beruvchi profili
    UserRegistrationSerializer — API orqali ro'yxatdan o'tish
"""
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User, WorkerProfile, EmployerProfile
from .phone import normalize_phone
from django.utils.translation import gettext as _


class WorkerProfileSerializer(serializers.ModelSerializer):
    """Ishchi profili uchun serializer."""

    class Meta:
        model = WorkerProfile
        fields = ("id", "skills", "rating", "completed_jobs_count", "bio")
        read_only_fields = ("id", "rating", "completed_jobs_count")


class EmployerProfileSerializer(serializers.ModelSerializer):
    """Ish beruvchi profili uchun serializer."""

    class Meta:
        model = EmployerProfile
        fields = ("id", "company_name", "rating", "posted_jobs_count")
        read_only_fields = ("id", "rating", "posted_jobs_count")


class UserSerializer(serializers.ModelSerializer):
    """
    Foydalanuvchi ma'lumotlarini ko'rsatish uchun serializer.
    Rolga qarab worker_profile yoki employer_profile kiritiriladi.
    """

    worker_profile = WorkerProfileSerializer(read_only=True)
    employer_profile = EmployerProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "phone_number",
            "first_name",
            "last_name",
            "role",
            "is_verified",
            "created_at",
            "worker_profile",
            "employer_profile",
        )
        # Telefon API orqali o'zgarmaydi (tasdiqlashsiz almashtirib bo'lmasin)
        read_only_fields = ("id", "phone_number", "created_at", "is_verified")

    def update(self, instance, validated_data):
        user = super().update(instance, validated_data)
        user.ensure_profile()  # rol almashgan bo'lsa yangi rol profili yaratiladi
        return user


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    API orqali yangi foydalanuvchini ro'yxatdan o'tkazish uchun serializer.
    Ro'yxatdan o'tishda rolga qarab tegishli profil avtomatik yaratiladi.
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        label="Parolni tasdiqlang",
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = (
            "phone_number",
            "first_name",
            "last_name",
            "role",
            "password",
            "password2",
        )

    def validate_phone_number(self, value):
        """Raqamni normallashtirish va takrorlanmasligini tekshirish."""
        value = normalize_phone(value)
        if value is None:
            raise serializers.ValidationError(_("Telefon raqam noto'g'ri. Namuna: +998901234567"))
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError(
                _("Bu telefon raqam allaqachon ro'yxatdan o'tgan.")
            )
        return value

    def validate(self, attrs):
        """Parollar mos kelishini tekshirish."""
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": _("Parollar mos kelmadi.")})
        return attrs

    def create(self, validated_data):
        """
        Foydalanuvchi yaratish.
        password2 olib tashlanadi, signal profil yaratishni bajaradi.
        """
        validated_data.pop("password2")
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
