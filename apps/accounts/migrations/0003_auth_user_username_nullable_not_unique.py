# Generated manually to support email-only login.

from django.db import migrations


def forwards(apps, schema_editor):
    vendor = schema_editor.connection.vendor

    if vendor == "sqlite":
        schema_editor.execute("PRAGMA foreign_keys=OFF;")
        schema_editor.execute("BEGIN;")
        schema_editor.execute(
            """
            CREATE TABLE "auth_user__new" (
                "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                "password" varchar(128) NOT NULL,
                "last_login" datetime NULL,
                "is_superuser" bool NOT NULL,
                "username" varchar(150) NULL,
                "last_name" varchar(150) NOT NULL,
                "email" varchar(254) NOT NULL,
                "is_staff" bool NOT NULL,
                "is_active" bool NOT NULL,
                "date_joined" datetime NOT NULL,
                "first_name" varchar(150) NOT NULL
            );
            """
        )
        schema_editor.execute(
            """
            INSERT INTO "auth_user__new"
            ("id","password","last_login","is_superuser","username","last_name","email","is_staff","is_active","date_joined","first_name")
            SELECT
            "id","password","last_login","is_superuser","username","last_name","email","is_staff","is_active","date_joined","first_name"
            FROM "auth_user";
            """
        )
        schema_editor.execute('DROP TABLE "auth_user";')
        schema_editor.execute('ALTER TABLE "auth_user__new" RENAME TO "auth_user";')
        schema_editor.execute("COMMIT;")
        schema_editor.execute("PRAGMA foreign_keys=ON;")
        return

    # Postgres/MySQL/etc: best-effort. (No state operation since auth_user is in contrib.auth.)
    try:
        schema_editor.execute('ALTER TABLE "auth_user" ALTER COLUMN "username" DROP NOT NULL;')
    except Exception:
        pass
    try:
        schema_editor.execute('ALTER TABLE "auth_user" DROP CONSTRAINT IF EXISTS "auth_user_username_key";')
    except Exception:
        pass


def backwards(apps, schema_editor):
    vendor = schema_editor.connection.vendor

    if vendor == "sqlite":
        schema_editor.execute("PRAGMA foreign_keys=OFF;")
        schema_editor.execute("BEGIN;")
        schema_editor.execute(
            """
            CREATE TABLE "auth_user__old" (
                "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                "password" varchar(128) NOT NULL,
                "last_login" datetime NULL,
                "is_superuser" bool NOT NULL,
                "username" varchar(150) NOT NULL UNIQUE,
                "last_name" varchar(150) NOT NULL,
                "email" varchar(254) NOT NULL,
                "is_staff" bool NOT NULL,
                "is_active" bool NOT NULL,
                "date_joined" datetime NOT NULL,
                "first_name" varchar(150) NOT NULL
            );
            """
        )
        schema_editor.execute(
            """
            INSERT INTO "auth_user__old"
            ("id","password","last_login","is_superuser","username","last_name","email","is_staff","is_active","date_joined","first_name")
            SELECT
            "id","password","last_login","is_superuser",COALESCE("username",""),"last_name","email","is_staff","is_active","date_joined","first_name"
            FROM "auth_user";
            """
        )
        schema_editor.execute('DROP TABLE "auth_user";')
        schema_editor.execute('ALTER TABLE "auth_user__old" RENAME TO "auth_user";')
        schema_editor.execute("COMMIT;")
        schema_editor.execute("PRAGMA foreign_keys=ON;")
        return

    try:
        schema_editor.execute('ALTER TABLE "auth_user" ALTER COLUMN "username" SET NOT NULL;')
    except Exception:
        pass
    try:
        schema_editor.execute('ALTER TABLE "auth_user" ADD CONSTRAINT "auth_user_username_key" UNIQUE ("username");')
    except Exception:
        pass


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("accounts", "0002_userprofile_last_verification_email_sent_at"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]

