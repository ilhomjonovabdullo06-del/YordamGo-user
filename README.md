# YordamGo — User (foydalanuvchilar) qismi

Asosiy loyihadan (YordamGo) ajratib olingan foydalanuvchi moduli. Fayllar o'zgartirilmagan, asl papka tuzilmasi saqlangan.

## Tarkib
- `apps/users/` — modellar (User, WorkerProfile, EmployerProfile), formalar, view'lar, DRF API, telefon bilan autentifikatsiya, login limiti, bloklangan sessiyani uzish, migratsiyalar
- `templates/users/` — ro'yxatdan o'tish, kirish, profil, profilni tahrirlash, parol va telefonni o'zgartirish shablonlari
- `tests/` — `test_users.py`, `test_auth_security.py`, `test_account.py` (+ umumiy `base.py`)

## Asosiy loyihaga qo'shish
Fayllarni asosiy loyihadagi shu nomli papkalarga joylashtiring (`apps/users`, `templates/users`, `tests`).
Ishlashi uchun `config/settings/base.py` da `AUTH_USER_MODEL = "users.User"`, `AUTHENTICATION_BACKENDS`
(`apps.users.backends.PhoneNumberBackend`) va `apps.users.middleware.BlockedUserMiddleware` sozlangan bo'lishi kerak.
