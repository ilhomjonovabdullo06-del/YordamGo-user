"""
Data migratsiya: mavjud telefon raqamlarni +998XXXXXXXXX ko'rinishiga keltiradi.

"901234567", "998901234567", "+998 90 123-45-67" → "+998901234567".
Tanib bo'lmaydigan raqamlarga tegilmaydi (login ularni asl ko'rinishida ham qabul qiladi).
Normallashgan raqam boshqa foydalanuvchida bo'lsa (bitta odamning ikki hisobi) —
migratsiya to'xtaydi va qaysi yozuv ekanini aytadi: bunday holat qo'lda hal qilinadi.
Orqaga qaytarish hech narsa qilmaydi (asl yozilish saqlanmagan).
"""
import re

from django.db import migrations

_SEPARATORS = re.compile(r"[\s\-().]")


def _normalize(value):
    # apps/users/phone.py dagi normalize_phone nusxasi: migratsiya kod o'zgarsa ham barqaror qolsin
    compact = _SEPARATORS.sub("", str(value or ""))
    if compact.startswith("00998"):
        compact = compact[2:]
    if re.fullmatch(r"\d{9}", compact):
        return "+998" + compact
    match = re.fullmatch(r"\+?998(\d{9})", compact)
    return "+998" + match.group(1) if match else None


def normalize_phone_numbers(apps, schema_editor):
    User = apps.get_model("users", "User")
    taken = set(User.objects.values_list("phone_number", flat=True))
    for user in User.objects.order_by("pk"):
        new = _normalize(user.phone_number)
        if not new or new == user.phone_number:
            continue
        if new in taken:
            raise RuntimeError(
                f"Telefon to'qnashuvi: foydalanuvchi #{user.pk} ({user.phone_number}) → {new} "
                "boshqa hisobda bor. Qaysi hisob qolishini qo'lda hal qiling va qayta migrate qiling."
            )
        taken.discard(user.phone_number)
        taken.add(new)
        User.objects.filter(pk=user.pk).update(phone_number=new)


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_user_is_blocked"),
    ]

    operations = [
        migrations.RunPython(normalize_phone_numbers, migrations.RunPython.noop),
    ]
