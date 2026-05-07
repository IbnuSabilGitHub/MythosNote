from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="last_verification_email_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
