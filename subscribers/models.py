from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class SubscriberProfile(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_ACTIVE = 'active'
    STATUS_ARTIST = 'artist'
    STATUS_PAST_DUE = 'past_due'
    STATUS_CANCELED = 'canceled'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_ARTIST, 'Artist (free access)'),
        (STATUS_PAST_DUE, 'Past Due'),
        (STATUS_CANCELED, 'Canceled'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscriber_profile')
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True)
    subscription_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    current_period_end = models.DateTimeField(null=True, blank=True)
    navidrome_user_id = models.CharField(max_length=100, blank=True)
    navidrome_access_error = models.BooleanField(default=False)
    library_access_granted = models.BooleanField(
        default=False,
        help_text='Whether we\'ve actually granted this user Navidrome library access. '
                  'Tracked separately from subscription_status so staff can grant/revoke manually.',
    )
    temporary_access_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def should_have_library_access(self):
        """Whether the subscriber's Stripe/temporary-access status entitles them to library access."""
        if self.subscription_status in (self.STATUS_ACTIVE, self.STATUS_ARTIST):
            return True
        if self.temporary_access_until and self.temporary_access_until > timezone.now():
            return True
        return False

    @property
    def temporary_access_active(self):
        return bool(self.temporary_access_until and self.temporary_access_until > timezone.now())

    def __str__(self):
        return f'{self.user.email} [{self.subscription_status}]'

    class Meta:
        verbose_name = 'Subscriber Profile'
        verbose_name_plural = 'Subscriber Profiles'
