"""
apps.users.views — foydalanuvchilar moduli uchun Django CBV va DRF APIView'lar.

Django View'lar (HTML shablonlar uchun):
    RegisterView    — Ro'yxatdan o'tish
    LoginView       — Tizimga kirish
    LogoutView      — Tizimdan chiqish
    ProfileView     — Profilni ko'rish
    ProfileEditView — Profilni tahrirlash

DRF API View'lar (mobil ilova uchun):
    APIRegisterView — API orqali ro'yxatdan o'tish
    APIProfileView  — API orqali profilni olish
"""
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import FormView, View, TemplateView

from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .forms import (
    UserRegistrationForm,
    UserLoginForm,
    WorkerProfileForm,
    EmployerProfileForm,
    UserProfileForm,
    ChangePasswordForm,
    ChangePhoneForm,
)
from .models import User
from .serializers import UserSerializer, UserRegistrationSerializer
from django.utils.translation import gettext as _


# ─────────────────────────────────────────────────────────────────────────────
# Django Class-Based Views (HTML shablonlar bilan ishlaydi)
# ─────────────────────────────────────────────────────────────────────────────


def safe_next(request, default):
    """?next= faqat shu sayt ichidagi manzil bo'lsa qabul qilinadi (ochiq redirect bo'lmasin)."""
    target = request.POST.get("next") or request.GET.get("next")
    if target and url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return target
    return default


class RegisterView(FormView):
    """
    Yangi foydalanuvchini ro'yxatdan o'tkazish; muvaffaqiyatli bo'lsa avtomatik kiradi.
    ?role=employer|worker — rol oldindan tanlanadi, ?next= — keyingi sahifa.
    Standart: ish beruvchi → e'lon berish, ishchi → xarita.
    """

    template_name = "users/register.html"
    form_class = UserRegistrationForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(safe_next(request, reverse("jobs:job_map")))
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        role = self.request.GET.get("role")
        initial["role"] = role if role in User.Role.values else User.Role.WORKER
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["next"] = safe_next(self.request, "")
        return context

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        self.created_user = user
        messages.success(
            self.request,
            _("Xush kelibsiz, %(user_first_name)s! Hisobingiz yaratildi.") % {"user_first_name": user.first_name},
        )
        return super().form_valid(form)

    def get_success_url(self):
        user = self.created_user
        default = reverse("jobs:job_create") if user.is_employer else reverse("jobs:job_map")
        return safe_next(self.request, default)


class LoginView(FormView):
    """
    Telefon raqam va parol bilan kirish. Kirgandan keyin ?next= (xavfsiz bo'lsa)
    yoki LOGIN_REDIRECT_URL (xarita).
    """

    template_name = "users/login.html"
    form_class = UserLoginForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(safe_next(request, settings.LOGIN_REDIRECT_URL))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["next"] = safe_next(self.request, "")
        return context

    def form_valid(self, form):
        user = form.get_user()
        # Bloklangan foydalanuvchini tizimga kiritmaylik
        if user.is_blocked:
            messages.error(
                self.request,
                _("Hisobingiz bloklangan. Administratsiya bilan bog'laning."),
            )
            return redirect("users:login")
        login(self.request, user)
        messages.success(self.request, _("Xush kelibsiz, %(value)s!") % {"value": user.first_name or user.get_full_name()})
        return super().form_valid(form)

    def get_success_url(self):
        return safe_next(self.request, settings.LOGIN_REDIRECT_URL)


class LogoutView(View):
    """Foydalanuvchini tizimdan chiqarish — faqat POST (begona sahifa GET bilan chiqara olmasin)."""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        logout(request)
        messages.info(request, _("Tizimdan chiqdingiz."))
        return redirect(settings.LOGOUT_REDIRECT_URL)


class ProfileView(LoginRequiredMixin, TemplateView):
    """
    Foydalanuvchi profilini ko'rish sahifasi.
    Rolga qarab worker_profile yoki employer_profile ko'rsatiladi.
    """

    template_name = "users/profile.html"
    login_url = reverse_lazy("users:login")

    def get_context_data(self, **kwargs):
        """Shablonga profilni uzatish."""
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["user"] = user

        context["profile"] = user.ensure_profile()
        context["profile_type"] = "worker" if user.is_worker else "employer"

        return context


class SwitchRoleView(LoginRequiredMixin, View):
    """Faol rejimni almashtirish (ishchi <-> ish beruvchi). Faqat POST; kerakli profil yaratiladi."""

    http_method_names = ["post"]
    login_url = reverse_lazy("users:login")

    def post(self, request, *args, **kwargs):
        user = request.user
        user.role = User.Role.EMPLOYER if user.is_worker else User.Role.WORKER
        user.save(update_fields=["role"])
        user.ensure_profile()
        if user.is_employer:
            messages.success(request, _("Ish beruvchi rejimiga o'tdingiz."))
            default = reverse("jobs:job_create")
        else:
            messages.success(request, _("Ishchi rejimiga o'tdingiz."))
            default = reverse("jobs:job_map")
        return redirect(safe_next(request, default))


class _AccountFormView(LoginRequiredMixin, FormView):
    """Parol/telefon o'zgartirish uchun umumiy asos (faqat kirgan foydalanuvchi, POST + CSRF)."""

    login_url = reverse_lazy("users:login")
    success_url = reverse_lazy("users:profile")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs


class ChangePasswordView(_AccountFormView):
    template_name = "users/change_password.html"

    def get_form_class(self):
        return ChangePasswordForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        update_session_auth_hash(self.request, form.user)  # boshqa qurilmalardagi sessiyalar tugaydi, shu qurilma qoladi
        messages.success(self.request, _("Parol o'zgartirildi."))
        return super().form_valid(form)


class ChangePhoneView(_AccountFormView):
    template_name = "users/change_phone.html"

    def get_form_class(self):
        return ChangePhoneForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = form.save()
        messages.success(self.request, _("Telefon raqam yangilandi. Endi %(phone)s bilan kirasiz.") % {"phone": user.phone_number})
        return super().form_valid(form)


class ProfileEditView(LoginRequiredMixin, View):
    """
    Profilni tahrirlash sahifasi.
    Rolga qarab to'g'ri forma ko'rsatiladi va saqlanadi.
    """

    template_name = "users/profile_edit.html"
    login_url = reverse_lazy("users:login")

    def _get_forms(self, request, data=None):
        """Rolga qarab tegishli formalarni qaytarish."""
        user = request.user
        user_form = UserProfileForm(data, instance=user)

        # Rol almashgan bo'lsa profil yo'q bo'lishi mumkin — yaratib olinadi (aks holda 500)
        profile = user.ensure_profile()
        form_class = WorkerProfileForm if user.is_worker else EmployerProfileForm
        profile_form = form_class(data, instance=profile)

        return user_form, profile_form

    def get(self, request, *args, **kwargs):
        """Tahrirlash formasini ko'rsatish."""
        from django.shortcuts import render
        user_form, profile_form = self._get_forms(request)
        return render(
            request,
            self.template_name,
            {"user_form": user_form, "profile_form": profile_form},
        )

    def post(self, request, *args, **kwargs):
        """Formani saqlash."""
        from django.shortcuts import render
        user_form, profile_form = self._get_forms(request, request.POST)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, _("Profilingiz muvaffaqiyatli yangilandi."))
            return redirect("users:profile")

        return render(
            request,
            self.template_name,
            {"user_form": user_form, "profile_form": profile_form},
        )


# ─────────────────────────────────────────────────────────────────────────────
# DRF API View'lar (mobil ilova yoki tashqi mijozlar uchun)
# ─────────────────────────────────────────────────────────────────────────────


class APIRegisterView(APIView):
    """
    API orqali yangi foydalanuvchini ro'yxatdan o'tkazish.

    POST /api/users/register/
    Body: { phone_number, first_name, last_name, role, password, password2 }
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    def post(self, request, *args, **kwargs):
        """Yangi foydalanuvchi yaratish."""
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {
                    "message": "Foydalanuvchi muvaffaqiyatli ro'yxatdan o'tdi.",
                    "user": UserSerializer(user).data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class APIProfileView(APIView):
    """
    Joriy foydalanuvchining profilini olish va yangilash.

    GET  /api/users/profile/ — profilni olish
    PATCH /api/users/profile/ — profilni yangilash
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """Profilni qaytarish."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        """Profilni qisman yangilash."""
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
