"""
Profil hisoblagichlari va reytinglarini bazadan qayta hisoblaydi (eski ma'lumotlarni tuzatish uchun).
"""
from django.core.management.base import BaseCommand

from apps.users.models import User
from apps.users.stats import refresh_employer_stats, refresh_ratings, refresh_worker_stats


class Command(BaseCommand):
    help = "Bajarilgan/e'lon qilingan ishlar soni va reytinglarni qayta hisoblaydi."

    def handle(self, *args, **options):
        total = 0
        for user in User.objects.all().iterator():
            refresh_worker_stats(user)
            refresh_employer_stats(user)
            refresh_ratings(user)
            total += 1
        self.stdout.write(f"Qayta hisoblandi: {total} foydalanuvchi")
