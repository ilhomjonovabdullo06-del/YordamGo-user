"""
apps.users.admin — foydalanuvchilar modeli uchun Django admin konfiguratsiyasi.

Ro'yxatdan o'tgan modellar:
    User            — custom foydalanuvchi modeli
    WorkerProfile   — ishchi profili
    EmployerProfile — ish beruvchi profili
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, WorkerProfile, EmployerProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom User admin — phone_number asosiy identifikator sifatida.
    """

    ordering = ["-created_at"]
    list_display = (
        "phone_number",
        "first_name",
        "last_name",
        "role",
        "is_verified",
        "is_active",
        "is_staff",
        "created_at",
    )
    list_filter = ("role", "is_verified", "is_active", "is_staff")
    search_fields = ("phone_number", "first_name", "last_name")
    readonly_fields = ("created_at",)

    # username maydoni yo'qligi uchun fieldsets qayta aniqlanadi
    fieldsets = (
        (None, {"fields": ("phone_number", "password")}),
        (
            _("Shaxsiy ma'lumotlar"),
            {"fields": ("first_name", "last_name", "role", "is_verified")},
        ),
        (
            _("Ruxsatlar"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Muhim sanalar"), {"fields": ("last_login", "created_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "phone_number",
                    "first_name",
                    "last_name",
                    "role",
                    "password1",
                    "password2",
                ),
            },
        ),
    )


@admin.register(WorkerProfile)
class WorkerProfileAdmin(admin.ModelAdmin):
    """Ishchi profili admin."""

    list_display = (
        "get_full_name",
        "get_phone",
        "rating",
        "completed_jobs_count",
        "created_at",
    )
    search_fields = ("user__phone_number", "user__first_name", "user__last_name")
    readonly_fields = ("rating", "completed_jobs_count", "created_at", "updated_at")
    list_filter = ("rating",)

    @admin.display(description="To'liq ism")
    def get_full_name(self, obj):
        return obj.user.get_full_name()

    @admin.display(description="Telefon raqam")
    def get_phone(self, obj):
        return obj.user.phone_number


@admin.register(EmployerProfile)
class EmployerProfileAdmin(admin.ModelAdmin):
    """Ish beruvchi profili admin."""

    list_display = (
        "get_full_name",
        "get_phone",
        "company_name",
        "rating",
        "posted_jobs_count",
        "created_at",
    )
    search_fields = (
        "user__phone_number",
        "user__first_name",
        "user__last_name",
        "company_name",
    )
    readonly_fields = ("rating", "posted_jobs_count", "created_at", "updated_at")
    list_filter = ("rating",)

    @admin.display(description="To'liq ism")
    def get_full_name(self, obj):
        return obj.user.get_full_name()

    @admin.display(description="Telefon raqam")
    def get_phone(self, obj):
        return obj.user.phone_number
