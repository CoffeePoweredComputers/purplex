"""
Add a unique constraint on auth_user.email to prevent duplicate accounts.

Django's default User model does not enforce email uniqueness at the DB level.
This caused a MultipleObjectsReturned crash when looking up users by email
(e.g., adding an instructor to a course).
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("users_app", "0005_userconsent_immutability_trigger"),
    ]

    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE auth_user ADD CONSTRAINT auth_user_email_unique UNIQUE (email);',
            reverse_sql='ALTER TABLE auth_user DROP CONSTRAINT auth_user_email_unique;',
        ),
    ]
