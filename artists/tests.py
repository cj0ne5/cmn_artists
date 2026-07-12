from django.contrib.auth.models import User
from django.test import TestCase, override_settings

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
