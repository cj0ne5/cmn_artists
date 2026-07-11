from django.contrib import admin

from .models import SubscriberProfile


@admin.register(SubscriberProfile)
class SubscriberProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'subscription_status', 'current_period_end', 'navidrome_user_id', 'created_at']
    list_filter = ['subscription_status']
    search_fields = ['user__email', 'stripe_customer_id', 'stripe_subscription_id']
    readonly_fields = ['created_at', 'stripe_customer_id', 'stripe_subscription_id', 'navidrome_user_id']
    raw_id_fields = ['user']
