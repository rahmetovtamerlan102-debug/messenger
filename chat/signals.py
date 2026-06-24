from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.postgres.search import SearchVector
from django.contrib.auth.models import User
from .models import Message, UserProfile

@receiver(post_save, sender=Message)
def update_search_vector(sender, instance, **kwargs):
    if instance.text:
        Message.objects.filter(pk=instance.pk).update(
            search_vector=SearchVector('text')
        )

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
