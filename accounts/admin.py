from django.contrib import admin
from .models import ArtistProfile, InviteRequest, Invitation


@admin.register(ArtistProfile)
class ArtistProfileAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'user', 'slug', 'created_at']
    list_filter = ['created_at']
    search_fields = ['display_name', 'user__email', 'slug']
    prepopulated_fields = {'slug': ('display_name',)}
    readonly_fields = ['created_at']
    raw_id_fields = ['user']


@admin.register(InviteRequest)
class InviteRequestAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['name', 'email']
    readonly_fields = ['created_at']


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ['invite_request', 'token', 'sent_at', 'accepted_at']
    readonly_fields = ['token', 'sent_at']
