from django import forms
from .models import ArtistProfile


class ArtistProfileForm(forms.ModelForm):
    class Meta:
        model = ArtistProfile
        fields = ['display_name', 'bio', 'photo']
        widgets = {
            'display_name': forms.TextInput(attrs={'placeholder': 'Your artist or band name'}),
            'bio': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Tell us about yourself as an artist...'}),
        }
        labels = {
            'display_name': 'artist / band name',
            'bio': 'bio',
            'photo': 'photo',
        }


class ArtistApplicationForm(forms.ModelForm):
    class Meta:
        model = ArtistProfile
        fields = ['display_name', 'note']
        widgets = {
            'display_name': forms.TextInput(attrs={'placeholder': 'Your artist or band name'}),
            'note': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Tell us about yourself and your music (optional)'}),
        }
        labels = {
            'display_name': 'artist / band name',
            'note': 'about you',
        }
