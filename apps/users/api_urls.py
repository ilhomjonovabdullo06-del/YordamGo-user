"""
apps.users.api_urls — DRF API endpoint'lari uchun URL konfiguratsiyasi.

URL'lar:
    /api/users/register/ — API orqali ro'yxatdan o'tish
    /api/users/profile/  — API orqali profilni olish/yangilash
"""
from django.urls import path

from .views import APIRegisterView, APIProfileView

app_name = "api_users"

urlpatterns = [
    path("users/register/", APIRegisterView.as_view(), name="api-register"),
    path("users/profile/", APIProfileView.as_view(), name="api-profile"),
]
