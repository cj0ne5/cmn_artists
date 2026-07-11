from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('subscribers', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscriberprofile',
            name='temporary_access_until',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
