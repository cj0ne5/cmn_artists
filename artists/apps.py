from django.apps import AppConfig


class ArtistsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'artists'
    label = 'accounts'  # keeps existing DB tables and migration history intact

    def ready(self):
        import artists.signals  # noqa: F401
