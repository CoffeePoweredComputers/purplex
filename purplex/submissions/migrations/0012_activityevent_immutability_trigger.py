"""
Add PostgreSQL trigger to enforce ActivityEvent immutability at the database level.

Python-level save()/delete() guards are bypassed by QuerySet.update(),
QuerySet.delete(), bulk_update(), and raw SQL. This trigger catches all of
those by blocking UPDATE and DELETE at the row level.

The permitted mutations are SET_NULL on user_id, problem_id, and course_id —
Django's on_delete=SET_NULL fires UPDATE ... SET <fk> = NULL when a related
object is deleted. The trigger allows this only when no other columns change.

Note: TRUNCATE bypasses row-level triggers entirely. Production should REVOKE
TRUNCATE on the application DB role as a separate infrastructure concern.
"""

from django.db import migrations

from purplex.submissions.sql import FORWARD_SQL, REVERSE_SQL


class Migration(migrations.Migration):

    dependencies = [
        ("submissions", "0011_activityevent"),
    ]

    operations = [
        migrations.RunSQL(sql=FORWARD_SQL, reverse_sql=REVERSE_SQL),
    ]
