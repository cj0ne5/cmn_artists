from django.contrib import admin
from .models import Album, Track


class TrackInline(admin.TabularInline):
    model = Track
    extra = 0
    fields = ['track_number', 'title', 'audio_file', 'duration_seconds', 'genre', 'isrc']
    readonly_fields = ['duration_seconds']


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ['title', 'artist', 'genre', 'release_year', 'track_count', 'created_at']
    list_filter = ['genre', 'release_year', 'created_at']
    search_fields = ['title', 'artist__display_name', 'artist__user__email', 'genre']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['created_at', 'updated_at']
    inlines = [TrackInline]
    raw_id_fields = ['artist']

    def track_count(self, obj):
        return obj.tracks.count()
    track_count.short_description = 'Tracks'


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'track_number', 'album', 'get_artist',
        'genre', 'duration_seconds', 'isrc', 'created_at',
    ]
    list_filter = ['genre', 'created_at']
    search_fields = ['title', 'album__title', 'album__artist__display_name', 'album__artist__user__email', 'isrc', 'composer']
    readonly_fields = ['duration_seconds', 'created_at', 'updated_at']
    raw_id_fields = ['album']

    def get_artist(self, obj):
        return obj.album.artist.display_name
    get_artist.short_description = 'Artist'
    get_artist.admin_order_field = 'album__artist__display_name'
