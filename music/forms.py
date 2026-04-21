from django import forms
from .models import Album, Track

CURRENT_YEAR = 2026


class AlbumForm(forms.ModelForm):
    class Meta:
        model = Album
        fields = ['title', 'release_year', 'genre', 'compilation', 'cover_art', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Album title'}),
            'release_year': forms.NumberInput(attrs={
                'min': 1900,
                'max': CURRENT_YEAR + 2,
                'placeholder': 'e.g. 2024',
            }),
            'genre': forms.TextInput(attrs={'placeholder': 'e.g. Jazz, Hip-Hop, Go-Go'}),
            'cover_art': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }
        labels = {
            'title': 'title',
            'release_year': 'year',
            'genre': 'genre',
            'compilation': 'this is a compilation album',
            'cover_art': 'cover art',
            'description': 'description',
        }


class TrackUploadForm(forms.ModelForm):
    class Meta:
        model = Track
        fields = ['title', 'track_number', 'audio_file']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Track title'}),
            'track_number': forms.NumberInput(attrs={'min': 1}),
            'audio_file': forms.ClearableFileInput(attrs={'accept': '.mp3,.flac,.m4a,.mp4,.ogg,.aac'}),
        }
        labels = {
            'title': 'title',
            'track_number': 'track number',
            'audio_file': 'audio file',
        }


class TrackUpdateForm(forms.ModelForm):
    class Meta:
        model = Track
        fields = ['title', 'track_number', 'audio_file']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Track title'}),
            'track_number': forms.NumberInput(attrs={'min': 1}),
            'audio_file': forms.ClearableFileInput(attrs={'accept': '.mp3,.flac,.m4a,.mp4,.ogg,.aac'}),
        }
        labels = {
            'title': 'title',
            'track_number': 'track number',
            'audio_file': 'audio file',
        }


class TrackMetadataForm(forms.ModelForm):
    class Meta:
        model = Track
        fields = [
            'title', 'artist', 'album_artist',
            'track_number', 'disc_number',
            'genre', 'composer', 'isrc', 'bpm', 'comment',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Track title'}),
            'artist': forms.TextInput(attrs={'placeholder': 'Leave blank to use your display name'}),
            'album_artist': forms.TextInput(attrs={'placeholder': 'Leave blank to use your display name'}),
            'track_number': forms.NumberInput(attrs={'min': 1}),
            'disc_number': forms.NumberInput(attrs={'min': 1}),
            'genre': forms.TextInput(attrs={'placeholder': 'e.g. Jazz, Hip-Hop, Go-Go'}),
            'composer': forms.TextInput(attrs={'placeholder': 'Composer name(s)'}),
            'isrc': forms.TextInput(attrs={'placeholder': 'e.g. US-S1Z-99-00001'}),
            'bpm': forms.NumberInput(attrs={'min': 1, 'max': 999}),
            'comment': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'title': 'title',
            'artist': 'artist',
            'album_artist': 'album artist',
            'track_number': 'track number',
            'disc_number': 'disc number',
            'genre': 'genre',
            'composer': 'composer',
            'isrc': 'ISRC',
            'bpm': 'BPM',
            'comment': 'comment',
        }
