import os
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify


def album_cover_path(instance, filename):
    """
    Save cover art as cover.jpg (or cover.png) directly inside the album's
    audio folder so Navidrome picks it up as a folder image.
    upload_to is called before Album.save(), so slug may not be set yet —
    we fall back to slugifying the title.
    """
    try:
        artist_slug = instance.artist.artist_profile.slug or slugify(instance.artist.email)
    except Exception:
        artist_slug = f'user-{instance.artist_id}'
    album_slug = instance.slug or slugify(instance.title) or f'album-{instance.pk or "new"}'
    from pathlib import Path as _Path
    ext = _Path(filename).suffix.lower()
    cover_name = 'cover.png' if ext == '.png' else 'cover.jpg'
    return f'music/{artist_slug}/{album_slug}/{cover_name}'


def track_upload_path(instance, filename):
    """Upload path: media/music/{artist_slug}/{album_slug}/{filename}"""
    try:
        artist_slug = instance.album.artist.artist_profile.slug or slugify(instance.album.artist.email)
    except Exception:
        artist_slug = f'user-{instance.album.artist.pk}'
    album_slug = instance.album.slug or slugify(instance.album.title) or f'album-{instance.album.pk}'
    return f'music/{artist_slug}/{album_slug}/{filename}'


class Album(models.Model):
    artist = models.ForeignKey(User, on_delete=models.CASCADE, related_name='albums')
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300, blank=True)
    release_year = models.PositiveIntegerField(blank=True, null=True)
    cover_art = models.ImageField(upload_to=album_cover_path, blank=True, null=True)
    genre = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    compilation = models.BooleanField(default=False, help_text='Mark as a various-artists compilation album.')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Album'
        verbose_name_plural = 'Albums'

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Album.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.title} ({self.artist})'

    @property
    def track_count(self):
        return self.tracks.count()


class Track(models.Model):
    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name='tracks')
    title = models.CharField(max_length=300)
    track_number = models.PositiveIntegerField(default=1)
    audio_file = models.FileField(upload_to=track_upload_path)
    duration_seconds = models.FloatField(blank=True, null=True, help_text='Populated automatically from audio file')

    # Editable metadata — synced to file tags on save
    artist = models.CharField(max_length=300, blank=True, help_text='Performing artist(s). Defaults to your display name if blank.')
    album_artist = models.CharField(max_length=300, blank=True, help_text='Primary artist credited for the album (TPE2). Should be the same across all tracks on an album.')
    disc_number = models.PositiveIntegerField(blank=True, null=True, help_text='Disc number for multi-disc albums. Leave blank for single-disc albums.')
    genre = models.CharField(max_length=100, blank=True)
    composer = models.CharField(max_length=300, blank=True)
    isrc = models.CharField(
        max_length=20,
        blank=True,
        help_text='International Standard Recording Code (e.g. US-S1Z-99-00001)'
    )
    bpm = models.PositiveIntegerField(blank=True, null=True, help_text='Beats per minute')
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['track_number', 'title']
        verbose_name = 'Track'
        verbose_name_plural = 'Tracks'

    def __str__(self):
        return f'{self.track_number}. {self.title} — {self.album.title}'

    @property
    def duration_display(self):
        if self.duration_seconds is None:
            return '—'
        total = int(self.duration_seconds)
        minutes = total // 60
        seconds = total % 60
        return f'{minutes}:{seconds:02d}'

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        _skip_metadata_write = kwargs.pop('_skip_metadata_write', False)
        super().save(*args, **kwargs)

        if self.audio_file:
            filepath = self.audio_file.path
            if is_new:
                # On initial upload, read metadata to populate blank fields
                from .utils import read_audio_metadata
                try:
                    meta = read_audio_metadata(filepath)
                    changed = False
                    for field in ('duration_seconds', 'artist', 'album_artist',
                                  'genre', 'composer', 'isrc', 'bpm', 'comment',
                                  'disc_number'):
                        if meta.get(field) and not getattr(self, field):
                            setattr(self, field, meta[field])
                            changed = True
                    if changed:
                        Track.objects.filter(pk=self.pk).update(
                            duration_seconds=self.duration_seconds,
                            artist=self.artist,
                            album_artist=self.album_artist,
                            disc_number=self.disc_number,
                            genre=self.genre,
                            composer=self.composer,
                            isrc=self.isrc,
                            bpm=self.bpm,
                            comment=self.comment,
                        )
                except Exception:
                    pass

            if not _skip_metadata_write:
                # Write metadata tags back to the audio file
                from .utils import write_audio_metadata
                try:
                    write_audio_metadata(filepath, self)
                except Exception:
                    pass
