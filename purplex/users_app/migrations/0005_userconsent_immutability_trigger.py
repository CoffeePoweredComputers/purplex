"""
Add PostgreSQL trigger to enforce UserConsent immutability at the database level.

Python-level save()/delete() guards are bypassed by QuerySet.update(),
QuerySet.delete(), bulk_update(), and raw SQL. This trigger catches all of
those by blocking UPDATE and DELETE at the row level.

The one permitted mutation is SET_NULL on user_id — Django's on_delete=SET_NULL
fires UPDATE ... SET user_id = NULL when a user is deleted. The trigger allows
this only when no other columns change.

Note: TRUNCATE bypasses row-level triggers entirely. Production should REVOKE
TRUNCATE on the application DB role as a separate infrastructure concern.
"""

from django.db import migrations

from purplex.users_app.sql import FORWARD_SQL, REVERSE_SQL


class Migration(migrations.Migration):

    dependencies = [
        ("users_app", "0004_userconsent_set_null_and_deletion_indexes"),
    ]

    operations = [
        migrations.RunSQL(sql=FORWARD_SQL, reverse_sql=REVERSE_SQL),
    ]
