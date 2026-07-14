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
    agree_to_terms = forms.BooleanField(
        required=True,
        label='I have read and agree to the Artist Agreement',
        error_messages={'required': 'You must agree to the Artist Agreement to submit your application.'},
    )

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
