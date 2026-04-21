import uuid

from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify


class ArtistProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='artist_profile')
    display_name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    photo = models.ImageField(upload_to='artist_photos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    tutorial_seen = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.display_name and not self.slug:
            base_slug = slugify(self.display_name)
            slug = base_slug
            counter = 1
            while ArtistProfile.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            self.slug = slug
        elif self.display_name and self.slug:
            pass
        super().save(*args, **kwargs)

    def __str__(self):
        return self.display_name

    class Meta:
        verbose_name = 'Artist Profile'
        verbose_name_plural = 'Artist Profiles'


class InviteRequest(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_DECLINED = 'declined'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_DECLINED, 'Declined'),
    ]
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    note = models.TextField(blank=True, help_text='Tell us about yourself and your music')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} <{self.email}> [{self.status}]'

    class Meta:
        ordering = ['-created_at']


class Invitation(models.Model):
    invite_request = models.OneToOneField(InviteRequest, on_delete=models.CASCADE, related_name='invitation')
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    sent_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    @property
    def is_accepted(self):
        return self.accepted_at is not None

    def __str__(self):
        return f'Invite for {self.invite_request.email}'
