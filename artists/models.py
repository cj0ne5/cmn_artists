from decimal import Decimal

from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify

MONTHLY_INCOME_PER_SUPPORTER = Decimal('3.00')


class ArtistProfile(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_DECLINED = 'declined'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_DECLINED, 'Declined'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='artist_profile')
    display_name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    photo = models.ImageField(upload_to='artist_photos/', blank=True, null=True)
    note = models.TextField(blank=True, help_text='Tell us about yourself and your music')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    tutorial_seen = models.BooleanField(default=False)

    @property
    def is_approved(self):
        return self.status == self.STATUS_APPROVED

    @property
    def supporter_count(self):
        """Count of registered subscribers currently designating this artist for support."""
        from subscribers.models import SubscriberProfile
        return self.supporters.filter(subscription_status=SubscriberProfile.STATUS_ACTIVE).count()

    @property
    def monthly_income(self):
        """Estimated monthly income at $3/supporter/month."""
        return self.supporter_count * MONTHLY_INCOME_PER_SUPPORTER

    def save(self, *args, **kwargs):
        if self.display_name and not self.slug:
            base_slug = slugify(self.display_name)
            slug = base_slug
            counter = 1
            while ArtistProfile.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.display_name

    class Meta:
        verbose_name = 'Artist Profile'
        verbose_name_plural = 'Artist Profiles'
