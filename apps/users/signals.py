"""
apps.users.signals — foydalanuvchi yaratilganda profil avtomatik yaratish signallari.

Signal:
    create_user_profile — User post_save signali orqali WorkerProfile
                          yoki EmployerProfile avtomatik yaratadi.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User, WorkerProfile, EmployerProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Yangi foydalanuvchi yaratilganda rolga qarab tegishli profil yaratadi.

    Args:
        sender   — Signal yuboruvchi model (User)
        instance — Yaratilgan yoki yangilangan User obyekti
        created  — True: yangi yaratilgan, False: yangilangan
    """
    if not created:
        return

    if instance.role == User.Role.WORKER:
        WorkerProfile.objects.get_or_create(user=instance)
    elif instance.role == User.Role.EMPLOYER:
        EmployerProfile.objects.get_or_create(user=instance)
