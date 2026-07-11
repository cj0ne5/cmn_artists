import logging

from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from django.contrib import messages

logger = logging.getLogger(__name__)


class NavidromeAccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        # Capture plaintext password before super() hashes it via user.set_password().
        # adapter.set_password() is NOT called during signup — allauth calls
        # user.set_password() directly inside save_user, so we must hook here.
        password = form.cleaned_data.get('password1') or form.cleaned_data.get('password')
        user = super().save_user(request, user, form, commit=commit)
        if commit and password:
            self._sync_navidrome(user, password, request)
        return user

    def set_password(self, user, password):
        # Called by allauth for password change and password reset flows,
        # but NOT for initial signup (see save_user above).
        # Note: allauth calls get_adapter() without a request here, so self.request is None.
        super().set_password(user, password)
        self._sync_navidrome(user, password, request=None)

    def _sync_navidrome(self, user, password, request):
        from artists.navidrome import create_navidrome_user, update_navidrome_password
        from subscribers.models import SubscriberProfile

        try:
            profile = SubscriberProfile.objects.get(user=user)
        except SubscriberProfile.DoesNotExist:
            logger.warning('No SubscriberProfile for %s during Navidrome sync', user.email)
            return

        is_new_account = not profile.navidrome_user_id
        try:
            navidrome_url = settings.NAVIDROME_BASE_URL
            if not navidrome_url:
                raise RuntimeError('NAVIDROME_BASE_URL is not configured')

            if profile.navidrome_user_id:
                update_navidrome_password(
                    base_url=navidrome_url,
                    admin_user=settings.NAVIDROME_ADMIN_USER,
                    admin_pass=settings.NAVIDROME_ADMIN_PASS,
                    nd_user_id=profile.navidrome_user_id,
                    new_password=password,
                )
            else:
                nd_user_id = create_navidrome_user(
                    base_url=navidrome_url,
                    admin_user=settings.NAVIDROME_ADMIN_USER,
                    admin_pass=settings.NAVIDROME_ADMIN_PASS,
                    username=user.email,
                    display_name=user.email.split('@')[0],
                    email=user.email,
                    password=password,
                )
                profile.navidrome_user_id = nd_user_id
                profile.save(update_fields=['navidrome_user_id'])
        except Exception:
            logger.exception('Failed to sync Navidrome for %s', user.email)
            if is_new_account and request:
                messages.error(
                    request,
                    'Your account was created, but we could not connect to the streaming server. '
                    'Please contact us so we can sort it out.'
                )
