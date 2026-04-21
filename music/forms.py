from django import forms
from .models import Album, Track

CURRENT_YEAR = 2026


class AlbumForm(forms.ModelForm):
    class Meta:
        model = Album
        fields = ['title', 'release_year', 'genre', 'cover_art', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Album title',
            }),
            'release_year': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1900,
                'max': CURRENT_YEAR + 2,
                'placeholder': 'e.g. 2024',
            }),
            'genre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Jazz, Hip-Hop, Go-Go',
            }),
            'cover_art': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'A brief description of this album...',
            }),
        }
        labels = {
            'title': 'Album Title',
            'release_year': 'Release Year',
            'genre': 'Genre',
            'cover_art': 'Cover Art',
            'description': 'Description',
        }


class TrackUploadForm(forms.ModelForm):
    """Form for initial track upload — title, number, and file."""
    class Meta:
        model = Track
        fields = ['title', 'track_number', 'audio_file']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Track title',
            }),
            'track_number': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
            }),
            'audio_file': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': '.mp3,.flac,.m4a,.mp4,.ogg,.aac',
            }),
        }
        labels = {
            'title': 'Track Title',
            'track_number': 'Track Number',
            'audio_file': 'Audio File',
        }


class TrackUpdateForm(forms.ModelForm):
    """Form for re-uploading a track (title, number, optional new file)."""
    class Meta:
        model = Track
        fields = ['title', 'track_number', 'audio_file']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Track title',
            }),
            'track_number': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
            }),
            'audio_file': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': '.mp3,.flac,.m4a,.mp4,.ogg,.aac',
            }),
        }


class TrackMetadataForm(forms.ModelForm):
    """Form for editing track metadata fields that sync to audio file tags."""
    class Meta:
        model = Track
        fields = [
            'title', 'track_number', 'genre', 'composer',
            'lyricist', 'isrc', 'bpm', 'comment',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Track title',
            }),
            'track_number': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
            }),
            'genre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Jazz, Hip-Hop',
            }),
            'composer': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Composer name(s)',
            }),
            'lyricist': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Lyricist name(s)',
            }),
            'isrc': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. US-S1Z-99-00001',
            }),
            'bpm': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 999,
                'placeholder': 'Beats per minute',
            }),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Any notes or comments about this track...',
            }),
        }
        labels = {
            'title': 'Track Title',
            'track_number': 'Track Number',
            'genre': 'Genre',
            'composer': 'Composer',
            'lyricist': 'Lyricist',
            'isrc': 'ISRC',
            'bpm': 'BPM',
            'comment': 'Comment / Notes',
        }
        help_texts = {
            'isrc': 'International Standard Recording Code (e.g. US-S1Z-99-00001)',
            'bpm': 'Beats per minute',
        }
