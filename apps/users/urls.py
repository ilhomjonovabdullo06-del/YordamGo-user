"""
apps.users.urls — foydalanuvchilar moduli uchun URL konfiguratsiyasi.

URL'lar:
    /users/register/     — Ro'yxatdan o'tish
    /users/login/        — Tizimga kirish
    /users/logout/       — Tizimdan chiqish
    /users/profile/      — Profilni ko'rish
    /users/profile/edit/ — Profilni tahrirlash
"""
from django.urls import path

from .views import (
    RegisterView,
    LoginView,
    LogoutView,
    ProfileView,
    ProfileEditView,
    SwitchRoleView,
    ChangePasswordView,
    ChangePhoneView,
)

app_name = "users"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/edit/", ProfileEditView.as_view(), name="profile-edit"),
    path("profile/password/", ChangePasswordView.as_view(), name="change-password"),
    path("profile/phone/", ChangePhoneView.as_view(), name="change-phone"),
    path("role/switch/", SwitchRoleView.as_view(), name="switch-role"),
]
