from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from .forms import ArtistProfileForm, InviteRequestForm, RegistrationForm
from .models import ArtistProfile, Invitation, InviteRequest


class ArtistProfileRequiredMixin(LoginRequiredMixin):
    """
    Ensures the user is logged in and has an artist profile.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        profile = getattr(request.user, 'artist_profile', None)
        if profile is None:
            messages.warning(request, 'Please complete your artist profile first.')
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = getattr(self.request.user, 'artist_profile', None)
        albums = self.request.user.albums.prefetch_related('tracks').order_by('-created_at')
        context['profile'] = profile
        context['albums'] = albums
        return context


class ProfileEditView(LoginRequiredMixin, UpdateView):
    model = ArtistProfile
    form_class = ArtistProfileForm
    template_name = 'accounts/profile_edit.html'
    success_url = reverse_lazy('profile')

    def get_object(self, queryset=None):
        profile, created = ArtistProfile.objects.get_or_create(
            user=self.request.user,
            defaults={'display_name': self.request.user.email.split('@')[0]}
        )
        return profile

    def form_valid(self, form):
        messages.success(self.request, 'Profile updated.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class InviteRequestView(CreateView):
    model = InviteRequest
    form_class = InviteRequestForm
    template_name = 'accounts/invite_request.html'
    success_url = reverse_lazy('invite-request-sent')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)


class InviteRequestSentView(TemplateView):
    template_name = 'accounts/invite_request_sent.html'


class AdminInviteListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = InviteRequest
    template_name = 'accounts/admin_invite_list.html'
    context_object_name = 'invite_requests'
    ordering = ['-created_at']

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pending_count'] = InviteRequest.objects.filter(status=InviteRequest.STATUS_PENDING).count()
        context['approved_count'] = InviteRequest.objects.filter(status=InviteRequest.STATUS_APPROVED).count()
        context['declined_count'] = InviteRequest.objects.filter(status=InviteRequest.STATUS_DECLINED).count()
        return context


class AdminInviteApproveView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, pk):
        from django.core.mail import send_mail
        from django.urls import reverse
        invite_req = get_object_or_404(InviteRequest, pk=pk)
        if invite_req.status != InviteRequest.STATUS_PENDING:
            messages.error(request, 'This request has already been processed.')
            return redirect('admin-invite-list')
        invite_req.status = InviteRequest.STATUS_APPROVED
        invite_req.save()
        invitation = Invitation.objects.create(invite_request=invite_req)
        register_url = request.build_absolute_uri(
            reverse('register-with-token', kwargs={'token': invitation.token})
        )
        send_mail(
            subject='Your invitation to Capital Music Network',
            message=(
                f"Hi {invite_req.name},\n\n"
                f"You've been invited to submit your music to the Capital Music Network.\n\n"
                f"Complete your registration here:\n{register_url}\n\n"
                f"This link is unique to you.\n\n"
                f"— Capital Music Network"
            ),
            from_email=None,
            recipient_list=[invite_req.email],
            fail_silently=False,
        )
        messages.success(request, f'Invitation sent to {invite_req.email}.')
        return redirect('admin-invite-list')


class AdminInviteDeclineView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, pk):
        invite_req = get_object_or_404(InviteRequest, pk=pk, status=InviteRequest.STATUS_PENDING)
        invite_req.status = InviteRequest.STATUS_DECLINED
        invite_req.save()
        messages.success(request, f'Request from {invite_req.email} declined.')
        return redirect('admin-invite-list')


class RegisterWithTokenView(View):
    template_name = 'accounts/register.html'

    def get_invitation(self, token):
        return get_object_or_404(Invitation, token=token, accepted_at=None)

    def get(self, request, token):
        if request.user.is_authenticated:
            return redirect('dashboard')
        invitation = self.get_invitation(token)
        form = RegistrationForm()
        return render(request, self.template_name, {'form': form, 'invitation': invitation})

    def post(self, request, token):
        invitation = self.get_invitation(token)
        form = RegistrationForm(request.POST)
        if form.is_valid():
            from allauth.account.models import EmailAddress
            from django.contrib.auth import login
            from django.utils import timezone as tz
            email = invitation.invite_request.email
            user = User.objects.create_user(
                username=email,
                email=email,
                password=form.cleaned_data['password1'],
            )
            EmailAddress.objects.create(user=user, email=email, primary=True, verified=True)
            profile = user.artist_profile
            profile.display_name = invitation.invite_request.name
            profile.save()
            invitation.accepted_at = tz.now()
            invitation.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f'Welcome, {profile.display_name}.')
            return redirect('tutorial')
        return render(request, self.template_name, {'form': form, 'invitation': invitation})


class TutorialView(LoginRequiredMixin, View):
    template_name = 'accounts/tutorial.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        profile = request.user.artist_profile
        profile.tutorial_seen = True
        profile.save()
        return redirect('dashboard')


class DashboardView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            profile = request.user.artist_profile
            if not profile.tutorial_seen:
                return redirect('tutorial')
        except Exception:
            pass
        albums = request.user.albums.prefetch_related('tracks')
        total_tracks = sum(a.track_count for a in albums)
        return render(request, 'dashboard.html', {
            'albums': albums,
            'total_tracks': total_tracks,
        })
