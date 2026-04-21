from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

from accounts.views import (
    AdminInviteApproveView,
    AdminInviteDeclineView,
    AdminInviteListView,
    DashboardView,
    InviteRequestSentView,
    InviteRequestView,
    RegisterWithTokenView,
    TutorialView,
)


def home_view(request):
    from django.shortcuts import render
    return render(request, 'home.html')


urlpatterns = [
    path('', home_view, name='home'),
    # Redirect direct signup attempts to the invite request form
    path('accounts/signup/', RedirectView.as_view(url='/request-invite/', permanent=False)),
    path('accounts/', include('allauth.urls')),
    path('profile/', include('accounts.urls')),
    path('music/', include('music.urls')),
    # Invite / registration flow
    path('request-invite/', InviteRequestView.as_view(), name='invite-request'),
    path('request-invite/sent/', InviteRequestSentView.as_view(), name='invite-request-sent'),
    path('admin-panel/invites/', AdminInviteListView.as_view(), name='admin-invite-list'),
    path('admin-panel/invites/<int:pk>/approve/', AdminInviteApproveView.as_view(), name='admin-invite-approve'),
    path('admin-panel/invites/<int:pk>/decline/', AdminInviteDeclineView.as_view(), name='admin-invite-decline'),
    path('register/<uuid:token>/', RegisterWithTokenView.as_view(), name='register-with-token'),
    path('tutorial/', TutorialView.as_view(), name='tutorial'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
