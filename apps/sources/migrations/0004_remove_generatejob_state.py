# State-only: move GenerateJob to apps.generate (table kept)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("sources", "0003_chatsession_chatmessage"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(
                    name="GenerateJob",
                ),
            ],
            database_operations=[],
        ),
    ]
