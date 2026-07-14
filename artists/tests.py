from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings

from .agreement import get_artist_agreement_text
from .models import ArtistProfile


class DashboardRedirectTests(TestCase):
    def test_staff_without_artist_profile_is_redirected_to_money(self):
        staff = User.objects.create_user(username='staff@example.com', email='staff@example.com', is_staff=True)
        self.client.force_login(staff)

        response = self.client.get('/dashboard/')

        self.assertRedirects(response, '/subscribe/admin/money/', fetch_redirect_response=False)

    def test_non_staff_without_artist_profile_is_redirected_to_subscriber_dashboard(self):
        user = User.objects.create_user(username='regular@example.com', email='regular@example.com')
        self.client.force_login(user)

        response = self.client.get('/dashboard/')

        self.assertRedirects(response, '/subscribe/dashboard/', fetch_redirect_response=False)

    @override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
    def test_staff_who_are_approved_artists_still_see_artist_dashboard(self):
        staff = User.objects.create_user(username='staffartist@example.com', email='staffartist@example.com', is_staff=True)
        ArtistProfile.objects.create(
            user=staff, display_name='Staff Artist',
            status=ArtistProfile.STATUS_APPROVED, tutorial_seen=True,
        )
        self.client.force_login(staff)

        response = self.client.get('/dashboard/')

        self.assertEqual(response.status_code, 200)


class ArtistApplicationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='applicant@example.com', email='applicant@example.com')
        self.client.force_login(self.user)

    @override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
    def test_application_page_shows_artist_agreement_text(self):
        response = self.client.get('/profile/apply/')

        self.assertContains(response, get_artist_agreement_text())

    @override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
    def test_submitting_without_agreeing_to_terms_is_rejected(self):
        response = self.client.post('/profile/apply/', {
            'display_name': 'Test Artist',
            'note': '',
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ArtistProfile.objects.filter(user=self.user).exists())
        self.assertFormError(response.context['form'], 'agree_to_terms', 'You must agree to the Artist Agreement to submit your application.')

    def test_submitting_with_agreement_creates_pending_application(self):
        response = self.client.post('/profile/apply/', {
            'display_name': 'Test Artist',
            'note': '',
            'agree_to_terms': 'on',
        })

        self.assertRedirects(response, '/dashboard/', fetch_redirect_response=False)
        profile = ArtistProfile.objects.get(user=self.user)
        self.assertEqual(profile.status, ArtistProfile.STATUS_PENDING)


class ArtistApplicationApprovalEmailTests(TestCase):
    def test_approval_email_includes_artist_agreement_text(self):
        staff = User.objects.create_user(username='staff@example.com', email='staff@example.com', is_staff=True)
        applicant = User.objects.create_user(username='applicant2@example.com', email='applicant2@example.com')
        profile = ArtistProfile.objects.create(
            user=applicant, display_name='Test Artist', status=ArtistProfile.STATUS_PENDING,
        )
        self.client.force_login(staff)

        self.client.post(f'/admin-panel/applications/{profile.pk}/approve/')

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(get_artist_agreement_text(), mail.outbox[0].body)
