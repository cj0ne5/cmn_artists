from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver

from .models import ArtistProfile


@receiver(post_save, sender=User)
def create_artist_profile(sender, instance, created, **kwargs):
    if created:
        # Default display_name to the username part of the email
        email = instance.email or ''
        display_name = email.split('@')[0] if email else instance.username or 'Artist'
        ArtistProfile.objects.create(user=instance, display_name=display_name)


@receiver(post_save, sender=User)
def save_artist_profile(sender, instance, **kwargs):
    if hasattr(instance, 'artist_profile'):
        instance.artist_profile.save()
