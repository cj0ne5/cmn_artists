import django.db.models.deletion
from django.db import migrations, models


def populate_artist_profile(apps, schema_editor):
    Album = apps.get_model('music', 'Album')
    ArtistProfile = apps.get_model('accounts', 'ArtistProfile')

    for album in Album.objects.select_related('artist').all():
        try:
            profile = ArtistProfile.objects.get(user=album.artist)
            album.artist_profile_new = profile
            album.save()
        except ArtistProfile.DoesNotExist:
            # Album owned by a user with no artist profile — skip; will be caught
            # if/when the schema makes the column non-nullable below.
            pass


class Migration(migrations.Migration):

    dependencies = [
        ('music', '0002_album_compilation_track_artist_album_artist_disc'),
        ('accounts', '0004_merge_application_into_profile'),
    ]

    operations = [
        # Step 1: add nullable FK to ArtistProfile alongside the existing artist (User) FK
        migrations.AddField(
            model_name='album',
            name='artist_profile_new',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='albums',
                to='accounts.artistprofile',
            ),
        ),
        # Step 2: populate it from existing user→profile relationships
        migrations.RunPython(populate_artist_profile, migrations.RunPython.noop),
        # Step 3: make non-nullable now that all rows are populated
        migrations.AlterField(
            model_name='album',
            name='artist_profile_new',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='albums',
                to='accounts.artistprofile',
            ),
        ),
        # Step 4: drop the old User FK
        migrations.RemoveField(model_name='album', name='artist'),
        # Step 5: rename the new field to 'artist'
        migrations.RenameField(model_name='album', old_name='artist_profile_new', new_name='artist'),
    ]
