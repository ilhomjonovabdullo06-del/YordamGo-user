"""
apps.users.middleware — bloklangan foydalanuvchining sessiyasini uzish.

Avval is_blocked faqat login formasida tekshirilardi: admin bloklagandan keyin ham ochiq
sessiya ishlayverardi. Endi har bir so'rovda tekshiriladi.
"""
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils.translation import gettext as _


class BlockedUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and user.is_blocked:
            logout(request)
            messages.error(request, _("Hisobingiz bloklangan. Administratsiya bilan bog'laning."))
            return redirect("users:login")
        return self.get_response(request)
