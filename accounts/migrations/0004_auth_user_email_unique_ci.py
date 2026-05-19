# Generated manually to keep email-only identity unique at the database layer.

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_auth_user_username_nullable_not_unique"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                'CREATE UNIQUE INDEX IF NOT EXISTS "auth_user_email_ci_unique" '
                'ON "auth_user" (LOWER("email")) WHERE "email" <> \'\';'
            ),
            reverse_sql='DROP INDEX IF EXISTS "auth_user_email_ci_unique";',
        ),
    ]
