from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("generate", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="generatejob",
            name="options",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="generatejob",
            name="source_ids",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="generatejob",
            name="title",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
    ]
