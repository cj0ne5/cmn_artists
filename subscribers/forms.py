from django import forms

from artists.models import ArtistProfile


class DesignatedArtistForm(forms.Form):
    artist_name = forms.CharField(
        required=False,
        label='Artist you want to support',
        widget=forms.TextInput(attrs={'placeholder': 'search for an artist'}),
    )

    def __init__(self, *args, subscriber, **kwargs):
        self.subscriber = subscriber
        super().__init__(*args, **kwargs)
        if not self.is_bound and subscriber.designated_artist:
            self.fields['artist_name'].initial = subscriber.designated_artist.display_name

    def clean_artist_name(self):
        name = self.cleaned_data['artist_name'].strip()
        if not name:
            return None
        try:
            return ArtistProfile.objects.get(display_name__iexact=name, status=ArtistProfile.STATUS_APPROVED)
        except ArtistProfile.DoesNotExist:
            raise forms.ValidationError('Please select an artist from the list.')

    def save(self):
        self.subscriber.designated_artist = self.cleaned_data['artist_name']
        self.subscriber.save(update_fields=['designated_artist'])
        return self.subscriber
