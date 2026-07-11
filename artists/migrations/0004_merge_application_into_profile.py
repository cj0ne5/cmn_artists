from django.db import migrations, models
from django.utils.text import slugify


def migrate_applications_to_profiles(apps, schema_editor):
    ArtistProfile = apps.get_model('accounts', 'ArtistProfile')
    ArtistApplication = apps.get_model('accounts', 'ArtistApplication')

    # All existing ArtistProfile records were previously approved through the old flow
    ArtistProfile.objects.all().update(status='approved')

    for app in ArtistApplication.objects.all():
        profile, created = ArtistProfile.objects.get_or_create(
            user=app.user,
            defaults={
                'display_name': app.display_name,
                'status': app.status,
                'note': app.note,
            }
        )
        if not created:
            # Approved artist — copy the application note across
            profile.note = app.note
            profile.save()
        elif not profile.slug:
            # Newly created profile for a pending/declined applicant — generate slug
            # (custom save() does not run in migrations)
            base_slug = slugify(app.display_name)
            slug = base_slug
            counter = 1
            while ArtistProfile.objects.filter(slug=slug).exclude(pk=profile.pk).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            ArtistProfile.objects.filter(pk=profile.pk).update(slug=slug)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_artistapplication_remove_invitation_remove_inviterequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='artistprofile',
            name='note',
            field=models.TextField(blank=True, help_text='Tell us about yourself and your music'),
        ),
        migrations.AddField(
            model_name='artistprofile',
            name='status',
            field=models.CharField(
                choices=[('pending', 'Pending'), ('approved', 'Approved'), ('declined', 'Declined')],
                default='pending',
                max_length=20,
            ),
        ),
        migrations.RunPython(migrate_applications_to_profiles, migrations.RunPython.noop),
        migrations.DeleteModel(name='ArtistApplication'),
    ]
