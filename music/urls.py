from django.urls import path
from . import views

urlpatterns = [
    path('albums/', views.AlbumListView.as_view(), name='album-list'),
    path('albums/new/', views.AlbumCreateView.as_view(), name='album-create'),
    path('albums/<int:pk>/', views.AlbumDetailView.as_view(), name='album-detail'),
    path('albums/<int:pk>/edit/', views.AlbumUpdateView.as_view(), name='album-update'),
    path('albums/<int:pk>/delete/', views.AlbumDeleteView.as_view(), name='album-delete'),
    path('albums/<int:album_pk>/tracks/new/', views.TrackCreateView.as_view(), name='track-create'),
    path('tracks/<int:pk>/edit/', views.TrackUpdateView.as_view(), name='track-update'),
    path('tracks/<int:pk>/metadata/', views.TrackMetadataView.as_view(), name='track-metadata'),
    path('tracks/<int:pk>/delete/', views.TrackDeleteView.as_view(), name='track-delete'),
]
