from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver

from .models import ArtistProfile


@receiver(post_save, sender=User)
def save_artist_profile(sender, instance, **kwargs):
    if hasattr(instance, 'artist_profile'):
        instance.artist_profile.save()
