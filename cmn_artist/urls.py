from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from artists.views import (
    AdminApplicationApproveView,
    AdminApplicationDeclineView,
    AdminApplicationListView,
    DashboardView,
    TutorialView,
)
from subscribers.views import AccountSettingsView, StripeWebhookView


def home_view(request):
    from django.shortcuts import render
    return render(request, 'home.html')


urlpatterns = [
    path('', home_view, name='home'),
    path('accounts/', include('allauth.urls')),
    path('hijack/', include('hijack.urls')),
    path('profile/', include('artists.urls')),
    path('music/', include('music.urls')),
    path('subscribe/', include('subscribers.urls')),
    # Artist application flow
    path('admin-panel/applications/', AdminApplicationListView.as_view(), name='admin-application-list'),
    path('admin-panel/applications/<int:pk>/approve/', AdminApplicationApproveView.as_view(), name='admin-application-approve'),
    path('admin-panel/applications/<int:pk>/decline/', AdminApplicationDeclineView.as_view(), name='admin-application-decline'),
    path('tutorial/', TutorialView.as_view(), name='tutorial'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('account/', AccountSettingsView.as_view(), name='account-settings'),
    # Stripe webhook (must be exempt from CSRF — handled by raw request body verification)
    path('stripe/webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
