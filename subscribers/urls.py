from django.urls import path
from . import views

urlpatterns = [
    path('', views.SubscribeLandingView.as_view(), name='subscribe-landing'),
    path('checkout/', views.SubscribeCheckoutView.as_view(), name='subscribe-checkout'),
    path('success/', views.SubscribeSuccessView.as_view(), name='subscribe-success'),
    path('canceled/', views.SubscribeCanceledView.as_view(), name='subscribe-canceled'),
    path('dashboard/', views.SubscriberDashboardView.as_view(), name='subscriber-dashboard'),
    path('cancel/', views.SubscribeCancelView.as_view(), name='subscribe-cancel'),
    path('admin/users/', views.AdminUserListView.as_view(), name='admin-user-list'),
    path('admin/money/', views.AdminMoneyView.as_view(), name='admin-money'),
    path('admin/users/<int:pk>/grant-access/', views.AdminGrantTemporaryAccessView.as_view(), name='admin-grant-temporary-access'),
    path('admin/users/<int:pk>/resync-navidrome/', views.AdminResyncNavidromeView.as_view(), name='admin-resync-navidrome'),
    path('admin/users/<int:pk>/grant-navidrome-access/', views.AdminGrantNavidromeAccessView.as_view(), name='admin-grant-navidrome-access'),
    path('admin/users/<int:pk>/revoke-navidrome-access/', views.AdminRevokeNavidromeAccessView.as_view(), name='admin-revoke-navidrome-access'),
]
