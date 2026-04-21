from django import forms
from .models import ArtistProfile, InviteRequest


class ArtistProfileForm(forms.ModelForm):
    class Meta:
        model = ArtistProfile
        fields = ['display_name', 'bio', 'photo']
        widgets = {
            'display_name': forms.TextInput(attrs={
                'placeholder': 'Your artist or band name',
            }),
            'bio': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Tell us about yourself as an artist...',
            }),
        }
        labels = {
            'display_name': 'artist / band name',
            'bio': 'bio',
            'photo': 'photo',
        }


class InviteRequestForm(forms.ModelForm):
    class Meta:
        model = InviteRequest
        fields = ['name', 'email', 'note']
        widgets = {
            'note': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Tell us about yourself and your music (optional)',
            }),
        }
        labels = {
            'note': 'about you',
        }


class RegistrationForm(forms.Form):
    password1 = forms.CharField(
        label='password',
        widget=forms.PasswordInput,
        min_length=8,
    )
    password2 = forms.CharField(
        label='confirm password',
        widget=forms.PasswordInput,
    )

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data
