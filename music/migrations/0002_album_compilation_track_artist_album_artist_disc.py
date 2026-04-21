from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('music', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='album',
            name='compilation',
            field=models.BooleanField(default=False, help_text='Mark as a various-artists compilation album.'),
        ),
        migrations.AddField(
            model_name='track',
            name='artist',
            field=models.CharField(blank=True, max_length=300, help_text='Performing artist(s). Defaults to your display name if blank.'),
        ),
        migrations.AddField(
            model_name='track',
            name='album_artist',
            field=models.CharField(blank=True, max_length=300, help_text='Primary artist credited for the album (TPE2). Should be the same across all tracks on an album.'),
        ),
        migrations.AddField(
            model_name='track',
            name='disc_number',
            field=models.PositiveIntegerField(blank=True, null=True, help_text='Disc number for multi-disc albums. Leave blank for single-disc albums.'),
        ),
        migrations.RemoveField(
            model_name='track',
            name='lyricist',
        ),
    ]
