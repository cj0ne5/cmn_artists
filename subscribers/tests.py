from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from artists.models import ArtistProfile
from .forms import DesignatedArtistForm
from .models import ArtistDesignationChange, SubscriberProfile, SubscriptionStatusChange


def make_artist(email='artist@example.com', display_name='QA Test Artist', status=ArtistProfile.STATUS_APPROVED):
    user = User.objects.create(email=email, username=email)
    return ArtistProfile.objects.create(user=user, display_name=display_name, status=status)


def make_subscriber(email='subscriber@example.com', is_staff=False):
    user = User.objects.create(email=email, username=email, is_staff=is_staff)
    return user.subscriber_profile


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class AdminUserListViewTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username='staff@example.com', email='staff@example.com', is_staff=True)
        self.client.force_login(self.staff)

    def test_active_subscriber_not_renewing_is_flagged(self):
        profile = make_subscriber('notrenewing@example.com')
        profile.subscription_status = SubscriberProfile.STATUS_ACTIVE
        profile.cancel_at_period_end = True
        profile.save()

        response = self.client.get('/subscribe/admin/users/')

        self.assertContains(response, 'not renewing')

    def test_active_subscriber_renewing_is_not_flagged(self):
        profile = make_subscriber('renewing@example.com')
        profile.subscription_status = SubscriberProfile.STATUS_ACTIVE
        profile.save()

        response = self.client.get('/subscribe/admin/users/')

        self.assertNotContains(response, 'not renewing')


class StaffLibraryAccessTests(TestCase):
    def test_staff_have_library_access_regardless_of_subscription_status(self):
        profile = make_subscriber('staffer@example.com', is_staff=True)
        self.assertEqual(profile.subscription_status, SubscriberProfile.STATUS_PENDING)
        self.assertTrue(profile.should_have_library_access)

    def test_non_staff_pending_subscriber_has_no_library_access(self):
        profile = make_subscriber('regular@example.com', is_staff=False)
        self.assertFalse(profile.should_have_library_access)


class SubscriptionStatusHistoryTests(TestCase):
    def test_status_change_is_recorded(self):
        profile = make_subscriber()
        profile.subscription_status = SubscriberProfile.STATUS_ACTIVE
        profile.save()
        profile.subscription_status = SubscriberProfile.STATUS_CANCELED
        profile.save()

        self.assertEqual(
            list(profile.status_history.order_by('changed_at').values_list('status', flat=True)),
            [SubscriberProfile.STATUS_ACTIVE, SubscriberProfile.STATUS_CANCELED],
        )

    def test_saving_without_status_change_does_not_record(self):
        profile = make_subscriber()
        profile.subscription_status = SubscriberProfile.STATUS_ACTIVE
        profile.save()
        profile.save()  # no-op change

        self.assertEqual(profile.status_history.count(), 1)

    def test_creating_a_profile_does_not_record_history(self):
        profile = make_subscriber()
        self.assertEqual(profile.status_history.count(), 0)


class ArtistDesignationHistoryTests(TestCase):
    def test_designating_an_artist_is_recorded(self):
        profile = make_subscriber()
        artist = make_artist()

        profile.designated_artist = artist
        profile.save()

        self.assertEqual(
            list(profile.artist_designation_history.values_list('artist', flat=True)),
            [artist.pk],
        )

    def test_clearing_designation_is_recorded_with_null_artist(self):
        profile = make_subscriber()
        artist = make_artist()
        profile.designated_artist = artist
        profile.save()

        profile.designated_artist = None
        profile.save()

        self.assertEqual(
            list(profile.artist_designation_history.order_by('changed_at').values_list('artist', flat=True)),
            [artist.pk, None],
        )

    def test_deleting_designated_artist_nulls_the_fk_without_error(self):
        profile = make_subscriber()
        artist = make_artist()
        profile.designated_artist = artist
        profile.save()

        artist.delete()

        profile.refresh_from_db()
        self.assertIsNone(profile.designated_artist)


class DesignatedArtistFormTests(TestCase):
    def test_valid_case_insensitive_artist_name_is_accepted(self):
        profile = make_subscriber()
        make_artist(display_name='QA Test Artist')

        form = DesignatedArtistForm({'artist_name': 'qa test artist'}, subscriber=profile)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        profile.refresh_from_db()
        self.assertEqual(profile.designated_artist.display_name, 'QA Test Artist')

    def test_unknown_artist_name_is_rejected(self):
        profile = make_subscriber()
        form = DesignatedArtistForm({'artist_name': 'Not A Real Artist'}, subscriber=profile)
        self.assertFalse(form.is_valid())

    def test_unapproved_artist_name_is_rejected(self):
        profile = make_subscriber()
        make_artist(display_name='Pending Artist', status=ArtistProfile.STATUS_PENDING)

        form = DesignatedArtistForm({'artist_name': 'Pending Artist'}, subscriber=profile)
        self.assertFalse(form.is_valid())

    def test_blank_name_clears_designation(self):
        profile = make_subscriber()
        artist = make_artist()
        profile.designated_artist = artist
        profile.save()

        form = DesignatedArtistForm({'artist_name': ''}, subscriber=profile)
        self.assertTrue(form.is_valid())
        form.save()

        profile.refresh_from_db()
        self.assertIsNone(profile.designated_artist)


class ArtistSupporterIncomeTests(TestCase):
    def test_only_active_subscribers_are_counted(self):
        artist = make_artist()

        active = make_subscriber('active@example.com')
        active.designated_artist = artist
        active.subscription_status = SubscriberProfile.STATUS_ACTIVE
        active.save()

        canceled = make_subscriber('canceled@example.com')
        canceled.designated_artist = artist
        canceled.subscription_status = SubscriberProfile.STATUS_CANCELED
        canceled.save()

        self.assertEqual(artist.supporter_count, 1)
        self.assertEqual(artist.monthly_income, Decimal('3.00'))

    def test_no_supporters_gives_zero_income(self):
        artist = make_artist()
        self.assertEqual(artist.supporter_count, 0)
        self.assertEqual(artist.monthly_income, Decimal('0.00'))


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class AdminMoneyViewTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username='staff@example.com', email='staff@example.com', is_staff=True)

    def test_requires_staff(self):
        non_staff = make_subscriber('nonstaff@example.com').user
        self.client.force_login(non_staff)
        response = self.client.get('/subscribe/admin/money/')
        self.assertEqual(response.status_code, 403)

    def test_totals_and_artist_breakdown(self):
        artist_a = make_artist('artist_a@example.com', 'Artist A')
        artist_b = make_artist('artist_b@example.com', 'Artist B')

        # two subscribers support Artist A, one supports nobody, one is canceled (not counted)
        s1 = make_subscriber('s1@example.com')
        s1.designated_artist = artist_a
        s1.subscription_status = SubscriberProfile.STATUS_ACTIVE
        s1.save()

        s2 = make_subscriber('s2@example.com')
        s2.designated_artist = artist_a
        s2.subscription_status = SubscriberProfile.STATUS_ACTIVE
        s2.save()

        s3 = make_subscriber('s3@example.com')
        s3.subscription_status = SubscriberProfile.STATUS_ACTIVE
        s3.save()

        s4 = make_subscriber('s4@example.com')
        s4.designated_artist = artist_b
        s4.subscription_status = SubscriberProfile.STATUS_CANCELED
        s4.save()

        self.client.force_login(self.staff)
        response = self.client.get('/subscribe/admin/money/')
        self.assertEqual(response.status_code, 200)

        ctx = response.context
        self.assertEqual(ctx['active_count'], 3)
        self.assertEqual(ctx['no_artist_count'], 1)
        self.assertEqual(ctx['cmn_total'], Decimal('12.00'))
        self.assertEqual(ctx['artist_total'], Decimal('108.00'))

        # $3 orphan pool split across 2 approved artists = $1.50 each
        self.assertEqual(ctx['orphan_share'], Decimal('1.50'))

        rows_by_name = {row['artist'].display_name: row for row in ctx['artist_rows']}
        self.assertEqual(rows_by_name['Artist A']['supporter_count'], 2)
        self.assertEqual(rows_by_name['Artist A']['monthly_income'], Decimal('7.50'))  # 2*3 + 1.50
        self.assertEqual(rows_by_name['Artist B']['supporter_count'], 0)
        self.assertEqual(rows_by_name['Artist B']['monthly_income'], Decimal('1.50'))  # 0*3 + 1.50

    def test_no_approved_artists_gives_zero_share(self):
        s = make_subscriber('lonely@example.com')
        s.subscription_status = SubscriberProfile.STATUS_ACTIVE
        s.save()

        self.client.force_login(self.staff)
        response = self.client.get('/subscribe/admin/money/')
        self.assertEqual(response.context['orphan_share'], Decimal('0.00'))
        self.assertEqual(response.context['artist_rows'], [])


class CancelAtPeriodEndTests(TestCase):
    def test_cancel_view_sets_flag(self):
        profile = make_subscriber('canceler@example.com')
        profile.stripe_subscription_id = 'sub_test123'
        profile.subscription_status = SubscriberProfile.STATUS_ACTIVE
        profile.save()

        self.client.force_login(profile.user)

        import unittest.mock as mock
        with mock.patch('subscribers.views.stripe.Subscription.modify') as modify:
            self.client.post('/subscribe/cancel/')
            modify.assert_called_once_with('sub_test123', cancel_at_period_end=True)

        profile.refresh_from_db()
        self.assertTrue(profile.cancel_at_period_end)
