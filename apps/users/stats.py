"""
apps.users.stats — profil hisoblagichlari va reytinglari (yagona joy).

Hisoblagichlar bazadan qayta hisoblanadi (increment emas) — shuning uchun bekor qilish,
muddat tugashi va qayta urinishlarda ham to'g'ri qoladi.
Reyting ROLLARNI ARALASHTIRMAYDI: ishchi reytingi — u ISHCHI sifatida olgan baholar
(ariza.worker == u), ish beruvchi reytingi — u ISH BERUVCHI sifatida olgan baholar
(e'lon.employer == u). Profil faol rolga emas, mavjudligiga qarab yangilanadi.
"""
from django.db.models import Avg


def refresh_worker_stats(user):
    from apps.applications.models import Application

    from .models import WorkerProfile

    count = Application.objects.filter(worker=user, status=Application.Status.COMPLETED).count()
    WorkerProfile.objects.filter(user=user).update(completed_jobs_count=count)
    return count


def refresh_employer_stats(user):
    from apps.jobs.models import Job

    from .models import EmployerProfile

    count = Job.objects.filter(employer=user).exclude(status=Job.Status.CANCELLED).count()
    EmployerProfile.objects.filter(user=user).update(posted_jobs_count=count)
    return count


def refresh_ratings(user):
    from apps.reviews.models import Review

    from .models import EmployerProfile, WorkerProfile

    reviews = Review.objects.filter(reviewee=user)
    as_worker = reviews.filter(application__worker=user).aggregate(a=Avg("rating"))["a"] or 0
    as_employer = reviews.filter(application__job__employer=user).aggregate(a=Avg("rating"))["a"] or 0
    WorkerProfile.objects.filter(user=user).update(rating=round(as_worker, 2))
    EmployerProfile.objects.filter(user=user).update(rating=round(as_employer, 2))
