"""
apps.users.forms — foydalanuvchilar uchun Django formalari.

Formalar:
    UserRegistrationForm — ro'yxatdan o'tish formasi
    UserLoginForm        — kirish formasi
    WorkerProfileForm    — ishchi profilini tahrirlash
    EmployerProfileForm  — ish beruvchi profilini tahrirlash
"""
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm

from . import throttle
from .models import User, WorkerProfile, EmployerProfile
from .phone import normalize_phone
from django.utils.translation import gettext as _, gettext_lazy

PHONE_FORMAT_ERROR = gettext_lazy("Telefon raqamni to'liq kiriting, masalan: +998 90 123 45 67")


class UserRegistrationForm(UserCreationForm):
    """
    Yangi foydalanuvchini ro'yxatdan o'tkazish formasi.
    Telefon raqam, ism, familiya, rol va parol so'raladi.
    """

    first_name = forms.CharField(
        max_length=100,
        label=gettext_lazy("Ism"),
        widget=forms.TextInput(attrs={"placeholder": gettext_lazy("Ismingiz"), "autocomplete": "given-name"}),
    )
    last_name = forms.CharField(
        max_length=100,
        label=gettext_lazy("Familiya"),
        widget=forms.TextInput(attrs={"placeholder": gettext_lazy("Familiyangiz"), "autocomplete": "family-name"}),
    )
    phone_number = forms.CharField(
        max_length=20,
        label=gettext_lazy("Telefon raqam"),
        widget=forms.TextInput(attrs={
            "placeholder": "90 123 45 67",
            "inputmode": "tel",
            "autocomplete": "tel-national",
            "class": "input-group__input",
        }),
    )
    role = forms.ChoiceField(
        choices=User.Role.choices,
        label=gettext_lazy("Men kimman"),
        widget=forms.RadioSelect,
    )
    password1 = forms.CharField(
        label=gettext_lazy("Parol"),
        help_text=gettext_lazy("Kamida 8 ta belgi; faqat raqamlardan iborat bo'lmasin."),
        widget=forms.PasswordInput(attrs={"placeholder": gettext_lazy("Parol o'ylab toping"), "autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label=gettext_lazy("Parolni takrorlang"),
        widget=forms.PasswordInput(attrs={"placeholder": gettext_lazy("Parolni qayta kiriting"), "autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = ("phone_number", "first_name", "last_name", "role", "password1", "password2")

    def clean_phone_number(self):
        """Raqamni +998XXXXXXXXX ko'rinishiga keltirish va takrorlanmasligini tekshirish."""
        phone = normalize_phone(self.cleaned_data.get("phone_number"))
        if phone is None:
            raise forms.ValidationError(PHONE_FORMAT_ERROR)
        if User.objects.filter(phone_number=phone).exists():
            raise forms.ValidationError(_("Bu telefon raqam allaqachon ro'yxatdan o'tgan."))
        return phone


class UserLoginForm(forms.Form):
    """
    Foydalanuvchini tizimga kiritish formasi.
    Telefon raqam va parol bilan autentifikatsiya.
    """

    phone_number = forms.CharField(
        max_length=20,
        label=gettext_lazy("Telefon raqam"),
        widget=forms.TextInput(attrs={
            "placeholder": "90 123 45 67",
            "inputmode": "tel",
            "autocomplete": "tel-national",
            "class": "input-group__input",
        }),
    )
    password = forms.CharField(
        label=gettext_lazy("Parol"),
        widget=forms.PasswordInput(attrs={"placeholder": gettext_lazy("Parolingiz"), "autocomplete": "current-password"}),
    )

    def __init__(self, *args, **kwargs):
        """Request obyektini saqlash."""
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        self.user = None

    def clean(self):
        """Foydalanuvchini autentifikatsiya qilish."""
        phone_number = self.cleaned_data.get("phone_number")
        password = self.cleaned_data.get("password")

        if phone_number and password:
            phone = normalize_phone(phone_number) or phone_number.strip()
            if throttle.is_locked(self.request, phone):
                raise forms.ValidationError(throttle.LOCKED_MESSAGE)
            self.user = authenticate(
                self.request,
                phone_number=phone,
                password=password,
            )
            if self.user is None:
                raise forms.ValidationError(
                    _("Telefon raqam yoki parol noto'g'ri. Qayta urinib ko'ring.")
                )
            if not self.user.is_active:
                raise forms.ValidationError(_("Bu hisob o'chirilgan."))
        return self.cleaned_data

    def get_user(self):
        """Autentifikatsiya qilingan foydalanuvchini qaytarish."""
        return self.user


class WorkerProfileForm(forms.ModelForm):
    """Ishchi profilini tahrirlash formasi."""

    class Meta:
        model = WorkerProfile
        fields = ("bio",)
        widgets = {
            "bio": forms.Textarea(
                attrs={"rows": 4, "placeholder": gettext_lazy("O'zingiz haqida qisqacha yozing...")}
            ),
        }
        labels = {
            "bio": gettext_lazy("O'zi haqida"),
        }


class EmployerProfileForm(forms.ModelForm):
    """Ish beruvchi profilini tahrirlash formasi."""

    class Meta:
        model = EmployerProfile
        fields = ("company_name",)
        widgets = {
            "company_name": forms.TextInput(
                attrs={"placeholder": gettext_lazy("Kompaniya nomi (ixtiyoriy)")}
            ),
        }
        labels = {
            "company_name": gettext_lazy("Kompaniya nomi"),
        }


class UserProfileForm(forms.ModelForm):
    """Asosiy profil ma'lumotlarini tahrirlash formasi."""

    class Meta:
        model = User
        fields = ("first_name", "last_name")
        labels = {
            "first_name": gettext_lazy("Ism"),
            "last_name": gettext_lazy("Familiya"),
        }
        widgets = {
            "first_name": forms.TextInput(attrs={"placeholder": gettext_lazy("Ismingiz")}),
            "last_name": forms.TextInput(attrs={"placeholder": gettext_lazy("Familiyangiz")}),
        }


# ── Hisob xavfsizligi: parol va telefon raqamni o'zgartirish ─────────────────────

def _account_key(user):
    return f"account:{user.pk}"


class ChangePasswordForm(PasswordChangeForm):
    """Eski parolni tasdiqlab yangisini o'rnatadi (Django validatorlari bilan). Eski parolni tanlash urinishlari cheklanadi."""

    def __init__(self, user, *args, request=None, **kwargs):
        self.request = request
        super().__init__(user, *args, **kwargs)
        self.fields["old_password"].label = gettext_lazy("Joriy parol")
        self.fields["new_password1"].label = gettext_lazy("Yangi parol")
        self.fields["new_password1"].help_text = gettext_lazy("Kamida 8 ta belgi; faqat raqamlardan iborat bo'lmasin.")
        self.fields["new_password2"].label = gettext_lazy("Yangi parolni takrorlang")

    def clean_old_password(self):
        if throttle.is_locked(self.request, _account_key(self.user)):
            raise forms.ValidationError(throttle.LOCKED_MESSAGE)
        try:
            return super().clean_old_password()
        except forms.ValidationError:
            throttle.register_failure(self.request, _account_key(self.user))
            raise


class ChangePhoneForm(forms.Form):
    """Telefon raqamni o'zgartirish: yangi raqam (normallashtiriladi, noyob) + joriy parol bilan tasdiqlash."""

    new_phone = forms.CharField(
        max_length=20,
        label=gettext_lazy("Yangi telefon raqam"),
        widget=forms.TextInput(attrs={
            "placeholder": "90 123 45 67", "inputmode": "tel", "autocomplete": "tel-national",
            "class": "input-group__input",
        }),
    )
    password = forms.CharField(
        label=gettext_lazy("Joriy parol"),
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, user, *args, request=None, **kwargs):
        self.user = user
        self.request = request
        super().__init__(*args, **kwargs)

    def clean_new_phone(self):
        phone = normalize_phone(self.cleaned_data["new_phone"])
        if phone is None:
            raise forms.ValidationError(PHONE_FORMAT_ERROR)
        if phone == self.user.phone_number:
            raise forms.ValidationError(_("Bu sizning hozirgi raqamingiz."))
        if User.objects.filter(phone_number=phone).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError(_("Bu telefon raqam allaqachon ro'yxatdan o'tgan."))
        return phone

    def clean_password(self):
        if throttle.is_locked(self.request, _account_key(self.user)):
            raise forms.ValidationError(throttle.LOCKED_MESSAGE)
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            throttle.register_failure(self.request, _account_key(self.user))
            raise forms.ValidationError(_("Joriy parol noto'g'ri."))
        return password

    def save(self):
        self.user.phone_number = self.cleaned_data["new_phone"]
        self.user.save(update_fields=["phone_number"])
        return self.user
