from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_inviterequest_invitation_artistprofile_tutorial_seen'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.DeleteModel(name='Invitation'),
        migrations.DeleteModel(name='InviteRequest'),
        migrations.CreateModel(
            name='ArtistApplication',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('display_name', models.CharField(help_text='Artist or band name', max_length=200)),
                ('note', models.TextField(blank=True, help_text='Tell us about yourself and your music')),
                ('status', models.CharField(
                    choices=[('pending', 'Pending'), ('approved', 'Approved'), ('declined', 'Declined')],
                    default='pending',
                    max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='artist_application',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Artist Application',
                'verbose_name_plural': 'Artist Applications',
                'ordering': ['-created_at'],
            },
        ),
    ]
