"""
apps.users.phone — telefon raqamlar bilan ishlash.

Yagona saqlash formati: +998XXXXXXXXX (12 raqam). Foydalanuvchi "90 123 45 67",
"901234567", "998901234567" yoki "+998 (90) 123-45-67" deb yozishi mumkin — hammasi
bir xil ko'rinishga keltiriladi.
"""
import re

_SEPARATORS = re.compile(r"[\s\-().]")
_LOCAL = re.compile(r"\d{9}")
_INTERNATIONAL = re.compile(r"\+?998(\d{9})")


def normalize_phone(value):
    """Raqamni +998XXXXXXXXX ko'rinishiga keltiradi; tanib bo'lmasa None qaytaradi."""
    if value is None:
        return None
    compact = _SEPARATORS.sub("", str(value))
    if compact.startswith("00998"):
        compact = compact[2:]
    if _LOCAL.fullmatch(compact):
        return "+998" + compact
    match = _INTERNATIONAL.fullmatch(compact)
    if match:
        return "+998" + match.group(1)
    return None


def format_phone(value):
    """'+998901234567' -> '+998 90 123 45 67' (tanib bo'lmasa o'zgarishsiz)."""
    normalized = normalize_phone(value)
    if not normalized:
        return value or ""
    d = normalized[4:]
    return f"+998 {d[:2]} {d[2:5]} {d[5:7]} {d[7:]}"


def mask_phone(value):
    """'+998901234567' -> '+998 90 *** ** 67' — to'lovgacha ko'rsatiladigan ko'rinish."""
    normalized = normalize_phone(value)
    if normalized:
        return f"+998 {normalized[4:6]} *** ** {normalized[-2:]}"
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) < 4:
        return "***"
    return f"{digits[:2]}{'*' * (len(digits) - 4)}{digits[-2:]}"
