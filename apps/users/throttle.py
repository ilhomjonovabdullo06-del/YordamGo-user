"""
apps.users.throttle — login urinishlarini cheklash (cache asosida).

Bitta raqamga 15 daqiqada 5 ta xato urinishdan keyin shu raqam bilan kirish vaqtincha
yopiladi. Bitta IP uchun chegara kengroq (20): mobil operatorlarda ko'p odam bitta IP
ortida bo'ladi. Standart LocMemCache bitta jarayon uchun — bitta serverli deploy'ga yetarli.
"""
from django.conf import settings
from django.utils.translation import gettext_lazy
from django.core.cache import cache

PHONE_LIMIT = 5
IP_LIMIT = 20
WINDOW_SECONDS = 15 * 60
LOCKED_MESSAGE = gettext_lazy("Juda ko'p muvaffaqiyatsiz urinish. 15 daqiqadan keyin qayta urinib ko'ring.")


def client_ip(request):
    if request is None:
        return "unknown"
    if getattr(settings, "USE_X_FORWARDED_FOR", False):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def _keys(request, phone):
    return (
        (f"login-fail:phone:{phone}", PHONE_LIMIT),
        (f"login-fail:ip:{client_ip(request)}", IP_LIMIT),
    )


def is_locked(request, phone):
    return any((cache.get(key) or 0) >= limit for key, limit in _keys(request, phone))


def register_failure(request, phone):
    for key, _limit in _keys(request, phone):
        cache.add(key, 0, WINDOW_SECONDS)  # oyna birinchi xatodan boshlanadi
        try:
            cache.incr(key)
        except ValueError:  # kalit shu orada muddati tugagan bo'lsa
            cache.set(key, 1, WINDOW_SECONDS)


def reset(phone):
    cache.delete(f"login-fail:phone:{phone}")
