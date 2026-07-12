import logging
from decimal import Decimal

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone as tz
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt

from artists.models import ArtistProfile
from artists.navidrome import grant_library_access, revoke_library_access
from .forms import DesignatedArtistForm
from .models import SubscriberProfile

logger = logging.getLogger(__name__)


class AccountSettingsView(LoginRequiredMixin, View):
    template_name = 'subscribers/account_settings.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self._context(request))

    def post(self, request, *args, **kwargs):
        profile = request.user.subscriber_profile
        form = DesignatedArtistForm(request.POST, subscriber=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Updated the artist you support.')
            return redirect('account-settings')
        messages.error(request, 'Please correct the errors below.')
        return render(request, self.template_name, self._context(request, form=form))

    def _context(self, request, form=None):
        profile = request.user.subscriber_profile
        return {
            'profile': profile,
            'artist_profile': getattr(request.user, 'artist_profile', None),
            'designated_artist_form': form or DesignatedArtistForm(subscriber=profile),
            'artist_names': ArtistProfile.objects.filter(
                status=ArtistProfile.STATUS_APPROVED
            ).order_by('display_name').values_list('display_name', flat=True),
        }


class SubscribeLandingView(TemplateView):
    template_name = 'subscribers/landing.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('subscriber-dashboard')
        return super().dispatch(request, *args, **kwargs)


class SubscribeCheckoutView(LoginRequiredMixin, View):
    def post(self, request):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        profile = request.user.subscriber_profile

        try:
            if not profile.stripe_customer_id:
                customer = stripe.Customer.create(
                    email=request.user.email,
                    metadata={'django_user_id': request.user.pk},
                )
                profile.stripe_customer_id = customer.id
                profile.save(update_fields=['stripe_customer_id'])

            session = stripe.checkout.Session.create(
                customer=profile.stripe_customer_id,
                mode='subscription',
                line_items=[{
                    'price': settings.STRIPE_SUBSCRIPTION_PRICE_ID,
                    'quantity': 1,
                }],
                success_url=request.build_absolute_uri('/subscribe/success/'),
                cancel_url=request.build_absolute_uri('/subscribe/canceled/'),
                metadata={'django_user_id': request.user.pk},
            )
            return redirect(session.url, permanent=False)
        except stripe.error.StripeError:
            logger.exception('Stripe error creating checkout session for %s', request.user.email)
            messages.error(request, 'Something went wrong with payment. Please try again.')
            return redirect('subscribe-landing')


class SubscribeSuccessView(LoginRequiredMixin, TemplateView):
    template_name = 'subscribers/success.html'


class SubscribeCanceledView(TemplateView):
    template_name = 'subscribers/canceled.html'


class SubscriberDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'subscribers/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.request.user.subscriber_profile
        context['profile'] = profile
        context['can_subscribe'] = profile.subscription_status in (
            SubscriberProfile.STATUS_PENDING,
            SubscriberProfile.STATUS_CANCELED,
        )
        context['support_email'] = settings.SUPPORT_EMAIL
        return context


class SubscribeCancelView(LoginRequiredMixin, View):
    def post(self, request):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        profile = request.user.subscriber_profile

        if not profile.stripe_subscription_id:
            messages.error(request, 'No active subscription found.')
            return redirect('subscriber-dashboard')

        try:
            stripe.Subscription.modify(
                profile.stripe_subscription_id,
                cancel_at_period_end=True,
            )
            profile.cancel_at_period_end = True
            profile.save(update_fields=['cancel_at_period_end'])
            messages.success(
                request,
                'Your subscription has been canceled. '
                'You\'ll keep access until the end of your current billing period.'
            )
        except stripe.error.StripeError:
            logger.exception('Stripe error canceling subscription for %s', request.user.email)
            messages.error(request, 'Something went wrong. Please try again.')

        return redirect('subscriber-dashboard')


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(View):
    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except (ValueError, stripe.error.SignatureVerificationError):
            return HttpResponse(status=400)

        event_type = event['type']
        data = event['data']['object']

        if event_type == 'checkout.session.completed':
            self._handle_checkout_completed(data)
        elif event_type == 'invoice.paid':
            self._handle_invoice_paid(data)
        elif event_type == 'invoice.payment_failed':
            self._handle_invoice_payment_failed(data)
        elif event_type == 'customer.subscription.deleted':
            self._handle_subscription_deleted(data)
        elif event_type == 'customer.subscription.updated':
            self._handle_subscription_updated(data)

        return HttpResponse(status=200)

    def _get_profile_by_customer(self, stripe_customer_id):
        try:
            return SubscriberProfile.objects.select_related('user').get(
                stripe_customer_id=stripe_customer_id
            )
        except SubscriberProfile.DoesNotExist:
            logger.error('No SubscriberProfile for Stripe customer %s', stripe_customer_id)
            return None

    def _handle_checkout_completed(self, session):
        profile = self._get_profile_by_customer(session.get('customer'))
        if not profile:
            return

        subscription_id = session.get('subscription')
        if subscription_id:
            profile.stripe_subscription_id = subscription_id

            stripe.api_key = settings.STRIPE_SECRET_KEY
            subscription = stripe.Subscription.retrieve(subscription_id)
            profile.current_period_end = tz.datetime.fromtimestamp(
                subscription['current_period_end'], tz=tz.utc
            )
            profile.cancel_at_period_end = subscription.get('cancel_at_period_end', False)

        profile.subscription_status = SubscriberProfile.STATUS_ACTIVE
        profile.save(update_fields=[
            'stripe_subscription_id', 'subscription_status', 'current_period_end', 'cancel_at_period_end',
        ])

        self._grant_access(profile)

    def _handle_invoice_paid(self, invoice):
        subscription_id = invoice.get('subscription')
        if not subscription_id:
            return
        try:
            profile = SubscriberProfile.objects.get(stripe_subscription_id=subscription_id)
        except SubscriberProfile.DoesNotExist:
            return

        period_end = invoice.get('lines', {}).get('data', [{}])[0].get('period', {}).get('end')
        if period_end:
            profile.current_period_end = tz.datetime.fromtimestamp(period_end, tz=tz.utc)

        if profile.subscription_status == SubscriberProfile.STATUS_PAST_DUE:
            profile.subscription_status = SubscriberProfile.STATUS_ACTIVE
            self._grant_access(profile)

        profile.save(update_fields=['current_period_end', 'subscription_status'])

    def _handle_invoice_payment_failed(self, invoice):
        subscription_id = invoice.get('subscription')
        if not subscription_id:
            return
        try:
            profile = SubscriberProfile.objects.get(stripe_subscription_id=subscription_id)
        except SubscriberProfile.DoesNotExist:
            return

        profile.subscription_status = SubscriberProfile.STATUS_PAST_DUE
        profile.save(update_fields=['subscription_status'])

    def _handle_subscription_deleted(self, subscription):
        try:
            profile = SubscriberProfile.objects.get(
                stripe_subscription_id=subscription.get('id', '')
            )
        except SubscriberProfile.DoesNotExist:
            return

        profile.subscription_status = SubscriberProfile.STATUS_CANCELED
        profile.cancel_at_period_end = False
        profile.save(update_fields=['subscription_status', 'cancel_at_period_end'])
        self._revoke_access(profile)

    def _handle_subscription_updated(self, subscription):
        try:
            profile = SubscriberProfile.objects.get(
                stripe_subscription_id=subscription.get('id', '')
            )
        except SubscriberProfile.DoesNotExist:
            return

        profile.cancel_at_period_end = subscription.get('cancel_at_period_end', False)
        period_end = subscription.get('current_period_end')
        if period_end:
            profile.current_period_end = tz.datetime.fromtimestamp(period_end, tz=tz.utc)
        profile.save(update_fields=['cancel_at_period_end', 'current_period_end'])

    def _grant_access(self, profile):
        navidrome_url = getattr(settings, 'NAVIDROME_BASE_URL', '')
        if not navidrome_url or not profile.navidrome_user_id:
            return
        try:
            grant_library_access(
                base_url=navidrome_url,
                admin_user=settings.NAVIDROME_ADMIN_USER,
                admin_pass=settings.NAVIDROME_ADMIN_PASS,
                nd_user_id=profile.navidrome_user_id,
                library_id=settings.NAVIDROME_LIBRARY_ID,
                sample_library_id=settings.NAVIDROME_SAMPLE_LIBRARY_ID,
            )
        except Exception:
            logger.exception('Failed to grant Navidrome access for %s', profile.user.email)
            profile.navidrome_access_error = True
            profile.save(update_fields=['navidrome_access_error'])
        else:
            profile.navidrome_access_error = False
            profile.library_access_granted = True
            profile.save(update_fields=['navidrome_access_error', 'library_access_granted'])

    def _revoke_access(self, profile):
        navidrome_url = getattr(settings, 'NAVIDROME_BASE_URL', '')
        if not navidrome_url or not profile.navidrome_user_id:
            return
        try:
            revoke_library_access(
                base_url=navidrome_url,
                admin_user=settings.NAVIDROME_ADMIN_USER,
                admin_pass=settings.NAVIDROME_ADMIN_PASS,
                nd_user_id=profile.navidrome_user_id,
                sample_library_id=settings.NAVIDROME_SAMPLE_LIBRARY_ID,
            )
        except Exception:
            logger.exception('Failed to revoke Navidrome access for %s', profile.user.email)
            profile.navidrome_access_error = True
            profile.save(update_fields=['navidrome_access_error'])
        else:
            profile.navidrome_access_error = False
            profile.library_access_granted = False
            profile.save(update_fields=['navidrome_access_error', 'library_access_granted'])


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff


class AdminUserListView(StaffRequiredMixin, View):
    template_name = 'subscribers/admin_user_list.html'

    def get(self, request):
        profiles = (
            SubscriberProfile.objects
            .select_related('user', 'user__artist_profile')
            .order_by('user__email')
        )
        return render(request, self.template_name, {'profiles': profiles})


class AdminMoneyView(StaffRequiredMixin, View):
    template_name = 'subscribers/admin_money.html'

    CMN_PER_SUBSCRIBER_YEAR = Decimal('4.00')
    ARTIST_PER_SUBSCRIBER_YEAR = Decimal('36.00')
    MONTHLY_PER_SUPPORTER = Decimal('3.00')

    def get(self, request):
        active_subscribers = SubscriberProfile.objects.filter(subscription_status=SubscriberProfile.STATUS_ACTIVE)
        active_count = active_subscribers.count()
        no_artist_count = active_subscribers.filter(designated_artist__isnull=True).count()

        artists = ArtistProfile.objects.filter(status=ArtistProfile.STATUS_APPROVED).annotate(
            direct_supporter_count=Count(
                'supporters',
                filter=Q(supporters__subscription_status=SubscriberProfile.STATUS_ACTIVE),
            )
        ).order_by('-direct_supporter_count', 'display_name')

        artist_count = artists.count()
        orphan_share = (
            (Decimal(no_artist_count) * self.MONTHLY_PER_SUPPORTER / artist_count)
            if artist_count else Decimal('0.00')
        )

        artist_rows = [
            {
                'artist': artist,
                'supporter_count': artist.direct_supporter_count,
                'monthly_income': (Decimal(artist.direct_supporter_count) * self.MONTHLY_PER_SUPPORTER) + orphan_share,
            }
            for artist in artists
        ]

        context = {
            'active_count': active_count,
            'no_artist_count': no_artist_count,
            'artist_count': artist_count,
            'cmn_total': active_count * self.CMN_PER_SUBSCRIBER_YEAR,
            'artist_total': active_count * self.ARTIST_PER_SUBSCRIBER_YEAR,
            'orphan_share': orphan_share,
            'artist_rows': artist_rows,
        }
        return render(request, self.template_name, context)


class AdminGrantTemporaryAccessView(StaffRequiredMixin, View):
    def post(self, request, pk):
        profile = get_object_or_404(SubscriberProfile, pk=pk)
        days_str = request.POST.get('days', '').strip()

        try:
            days = int(days_str)
            if days < 1:
                raise ValueError
        except ValueError:
            messages.error(request, 'Enter a valid number of days (minimum 1).')
            return redirect('admin-user-list')

        until = tz.now() + tz.timedelta(days=days)
        profile.temporary_access_until = until
        profile.save(update_fields=['temporary_access_until'])

        navidrome_url = getattr(settings, 'NAVIDROME_BASE_URL', '')
        if navidrome_url and profile.navidrome_user_id and not profile.subscription_status in (
            SubscriberProfile.STATUS_ACTIVE, SubscriberProfile.STATUS_ARTIST
        ):
            try:
                grant_library_access(
                    base_url=navidrome_url,
                    admin_user=settings.NAVIDROME_ADMIN_USER,
                    admin_pass=settings.NAVIDROME_ADMIN_PASS,
                    nd_user_id=profile.navidrome_user_id,
                    library_id=settings.NAVIDROME_LIBRARY_ID,
                    sample_library_id=settings.NAVIDROME_SAMPLE_LIBRARY_ID,
                )
            except Exception:
                logger.exception('Failed to grant temporary Navidrome access for %s', profile.user.email)
                profile.navidrome_access_error = True
                profile.save(update_fields=['navidrome_access_error'])
                messages.warning(request, f'Access record saved but Navidrome grant failed for {profile.user.email}.')
                return redirect('admin-user-list')
            else:
                profile.navidrome_access_error = False
                profile.library_access_granted = True
                profile.save(update_fields=['navidrome_access_error', 'library_access_granted'])

        messages.success(
            request,
            f'Temporary access granted to {profile.user.email} until {until.strftime("%b %d, %Y")}. '
            f'Run revoke_expired_access hourly via cron to auto-expire.'
        )
        return redirect('admin-user-list')


class AdminResyncNavidromeView(StaffRequiredMixin, View):
    def post(self, request, pk):
        import secrets
        from artists.navidrome import create_navidrome_user

        profile = get_object_or_404(SubscriberProfile, pk=pk)

        if profile.navidrome_user_id:
            messages.info(request, f'{profile.user.email} already has a Navidrome ID ({profile.navidrome_user_id}).')
            return redirect('admin-user-list')

        navidrome_url = getattr(settings, 'NAVIDROME_BASE_URL', '')
        if not navidrome_url:
            messages.error(request, 'NAVIDROME_BASE_URL is not configured.')
            return redirect('admin-user-list')

        # Create with a random password. The user must reset their password
        # via "forgot password" to sync their real password to Navidrome.
        temp_password = secrets.token_urlsafe(32)
        try:
            nd_user_id = create_navidrome_user(
                base_url=navidrome_url,
                admin_user=settings.NAVIDROME_ADMIN_USER,
                admin_pass=settings.NAVIDROME_ADMIN_PASS,
                username=profile.user.email,
                display_name=profile.user.email.split('@')[0],
                email=profile.user.email,
                password=temp_password,
            )
            profile.navidrome_user_id = nd_user_id
            profile.save(update_fields=['navidrome_user_id'])
            messages.success(
                request,
                f'Navidrome account created for {profile.user.email} (ID: {nd_user_id}). '
                f'They must reset their password to activate streaming access.'
            )
        except Exception:
            logger.exception('Admin re-sync failed for %s', profile.user.email)
            messages.error(request, f'Failed to create Navidrome account for {profile.user.email}. Check logs.')

        return redirect('admin-user-list')


class AdminGrantNavidromeAccessView(StaffRequiredMixin, View):
    """Grant Navidrome library access, regardless of Stripe subscription status. For manual/testing use."""

    def post(self, request, pk):
        profile = get_object_or_404(SubscriberProfile, pk=pk)

        navidrome_url = getattr(settings, 'NAVIDROME_BASE_URL', '')
        if not navidrome_url or not profile.navidrome_user_id:
            messages.error(request, f'{profile.user.email} has no Navidrome account to grant access to.')
            return redirect('admin-user-list')

        try:
            grant_library_access(
                base_url=navidrome_url,
                admin_user=settings.NAVIDROME_ADMIN_USER,
                admin_pass=settings.NAVIDROME_ADMIN_PASS,
                nd_user_id=profile.navidrome_user_id,
                library_id=settings.NAVIDROME_LIBRARY_ID,
                sample_library_id=settings.NAVIDROME_SAMPLE_LIBRARY_ID,
            )
        except Exception:
            logger.exception('Admin Navidrome grant failed for %s', profile.user.email)
            profile.navidrome_access_error = True
            profile.save(update_fields=['navidrome_access_error'])
            messages.error(request, f'Navidrome grant failed for {profile.user.email}. Check logs.')
            return redirect('admin-user-list')

        profile.navidrome_access_error = False
        profile.library_access_granted = True
        profile.save(update_fields=['navidrome_access_error', 'library_access_granted'])
        messages.success(request, f'Navidrome library access granted for {profile.user.email}.')
        return redirect('admin-user-list')


class AdminRevokeNavidromeAccessView(StaffRequiredMixin, View):
    """Revoke Navidrome library access, regardless of Stripe subscription status. For manual/testing use."""

    def post(self, request, pk):
        profile = get_object_or_404(SubscriberProfile, pk=pk)

        navidrome_url = getattr(settings, 'NAVIDROME_BASE_URL', '')
        if not navidrome_url or not profile.navidrome_user_id:
            messages.error(request, f'{profile.user.email} has no Navidrome account to revoke access from.')
            return redirect('admin-user-list')

        try:
            revoke_library_access(
                base_url=navidrome_url,
                admin_user=settings.NAVIDROME_ADMIN_USER,
                admin_pass=settings.NAVIDROME_ADMIN_PASS,
                nd_user_id=profile.navidrome_user_id,
                sample_library_id=settings.NAVIDROME_SAMPLE_LIBRARY_ID,
            )
        except Exception:
            logger.exception('Admin Navidrome revoke failed for %s', profile.user.email)
            profile.navidrome_access_error = True
            profile.save(update_fields=['navidrome_access_error'])
            messages.error(request, f'Navidrome revoke failed for {profile.user.email}. Check logs.')
            return redirect('admin-user-list')

        profile.navidrome_access_error = False
        profile.library_access_granted = False
        profile.save(update_fields=['navidrome_access_error', 'library_access_granted'])
        messages.success(request, f'Navidrome library access revoked for {profile.user.email}.')
        return redirect('admin-user-list')
