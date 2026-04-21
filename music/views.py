import os
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, FormView
)
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import Http404

from .models import Album, Track
from .forms import AlbumForm, TrackUploadForm, TrackUpdateForm, TrackMetadataForm

logger = logging.getLogger(__name__)


class OwnerAlbumMixin(LoginRequiredMixin):
    """Ensures the album belongs to the logged-in user."""

    def get_album(self):
        album = get_object_or_404(Album, pk=self.kwargs.get('pk') or self.kwargs.get('album_pk'))
        if album.artist != self.request.user:
            raise Http404('Album not found.')
        return album


class AlbumListView(LoginRequiredMixin, ListView):
    model = Album
    template_name = 'music/album_list.html'
    context_object_name = 'albums'

    def get_queryset(self):
        return Album.objects.filter(artist=self.request.user).prefetch_related('tracks')


class AlbumCreateView(LoginRequiredMixin, CreateView):
    model = Album
    form_class = AlbumForm
    template_name = 'music/album_form.html'

    def form_valid(self, form):
        form.instance.artist = self.request.user
        messages.success(self.request, f'Album "{form.instance.title}" created successfully.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('album-detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Create'
        context['page_title'] = 'Add New Album'
        return context


class AlbumDetailView(LoginRequiredMixin, DetailView):
    model = Album
    template_name = 'music/album_detail.html'
    context_object_name = 'album'

    def get_object(self, queryset=None):
        album = get_object_or_404(Album, pk=self.kwargs['pk'])
        if album.artist != self.request.user:
            raise Http404('Album not found.')
        return album

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tracks'] = self.object.tracks.all()
        return context


class AlbumUpdateView(LoginRequiredMixin, UpdateView):
    model = Album
    form_class = AlbumForm
    template_name = 'music/album_form.html'

    def get_object(self, queryset=None):
        album = get_object_or_404(Album, pk=self.kwargs['pk'])
        if album.artist != self.request.user:
            raise Http404('Album not found.')
        return album

    def form_valid(self, form):
        cover_changed = 'cover_art' in form.changed_data
        response = super().form_valid(form)
        if cover_changed and self.object.cover_art:
            # Re-embed the new cover into all existing track files
            from .utils import write_audio_metadata
            for track in self.object.tracks.all():
                if track.audio_file:
                    try:
                        write_audio_metadata(track.audio_file.path, track)
                    except Exception:
                        pass
        messages.success(self.request, f'Album "{self.object.title}" updated.')
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('album-detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Update'
        context['page_title'] = f'Edit Album: {self.object.title}'
        return context


class AlbumDeleteView(LoginRequiredMixin, DeleteView):
    model = Album
    template_name = 'music/album_confirm_delete.html'
    success_url = reverse_lazy('album-list')
    context_object_name = 'album'

    def get_object(self, queryset=None):
        album = get_object_or_404(Album, pk=self.kwargs['pk'])
        if album.artist != self.request.user:
            raise Http404('Album not found.')
        return album

    def form_valid(self, form):
        album = self.get_object()
        album_title = album.title

        # Delete audio files from disk for all tracks
        for track in album.tracks.all():
            if track.audio_file:
                try:
                    file_path = track.audio_file.path
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                except Exception as exc:
                    logger.warning('Could not delete track file %s: %s', track.audio_file, exc)

        # Delete album cover from disk
        if album.cover_art:
            try:
                cover_path = album.cover_art.path
                if os.path.isfile(cover_path):
                    os.remove(cover_path)
            except Exception as exc:
                logger.warning('Could not delete cover art %s: %s', album.cover_art, exc)

        messages.success(self.request, f'Album "{album_title}" and all its tracks have been deleted.')
        return super().form_valid(form)


class TrackCreateView(LoginRequiredMixin, CreateView):
    model = Track
    form_class = TrackUploadForm
    template_name = 'music/track_form.html'

    def get_album(self):
        album = get_object_or_404(Album, pk=self.kwargs['album_pk'])
        if album.artist != self.request.user:
            raise Http404('Album not found.')
        return album

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['album'] = self.get_album()
        context['action'] = 'Upload'
        context['page_title'] = 'Upload Track'
        return context

    def form_valid(self, form):
        album = self.get_album()
        form.instance.album = album
        messages.success(self.request, f'Track "{form.instance.title}" uploaded successfully.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('album-detail', kwargs={'pk': self.object.album.pk})


class TrackUpdateView(LoginRequiredMixin, UpdateView):
    model = Track
    form_class = TrackUpdateForm
    template_name = 'music/track_form.html'

    def get_object(self, queryset=None):
        track = get_object_or_404(Track, pk=self.kwargs['pk'])
        if track.album.artist != self.request.user:
            raise Http404('Track not found.')
        return track

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['album'] = self.object.album
        context['action'] = 'Update'
        context['page_title'] = f'Edit Track: {self.object.title}'
        return context

    def form_valid(self, form):
        messages.success(self.request, f'Track "{form.instance.title}" updated.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('album-detail', kwargs={'pk': self.object.album.pk})


class TrackMetadataView(LoginRequiredMixin, UpdateView):
    model = Track
    form_class = TrackMetadataForm
    template_name = 'music/track_metadata.html'

    def get_object(self, queryset=None):
        track = get_object_or_404(Track, pk=self.kwargs['pk'])
        if track.album.artist != self.request.user:
            raise Http404('Track not found.')
        return track

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['track'] = self.object
        context['album'] = self.object.album
        return context

    def form_valid(self, form):
        messages.success(
            self.request,
            f'Metadata for "{form.instance.title}" saved and file tags updated.'
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('album-detail', kwargs={'pk': self.object.album.pk})


class TrackDeleteView(LoginRequiredMixin, DeleteView):
    model = Track
    template_name = 'music/track_confirm_delete.html'
    context_object_name = 'track'

    def get_object(self, queryset=None):
        track = get_object_or_404(Track, pk=self.kwargs['pk'])
        if track.album.artist != self.request.user:
            raise Http404('Track not found.')
        return track

    def form_valid(self, form):
        track = self.get_object()
        track_title = track.title
        album_pk = track.album.pk

        # Delete audio file from disk
        if track.audio_file:
            try:
                file_path = track.audio_file.path
                if os.path.isfile(file_path):
                    os.remove(file_path)
            except Exception as exc:
                logger.warning('Could not delete audio file %s: %s', track.audio_file, exc)

        messages.success(self.request, f'Track "{track_title}" has been deleted.')
        # Store album pk before deletion
        self._album_pk = album_pk
        return super().form_valid(form)

    def get_success_url(self):
        album_pk = getattr(self, '_album_pk', None) or self.object.album.pk
        return reverse('album-detail', kwargs={'pk': album_pk})
