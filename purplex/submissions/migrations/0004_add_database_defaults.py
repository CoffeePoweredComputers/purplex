# Generated manually to add database-level defaults

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("submissions", "0003_add_submission_grading_fields"),
    ]

    operations = [
        # Add database-level default for comprehension_level
        migrations.RunSQL(
            "ALTER TABLE submissions_submission ALTER COLUMN comprehension_level SET DEFAULT 'not_evaluated';",
            reverse_sql="ALTER TABLE submissions_submission ALTER COLUMN comprehension_level DROP DEFAULT;",
        ),
        # Add database-level default for is_correct
        migrations.RunSQL(
            "ALTER TABLE submissions_submission ALTER COLUMN is_correct SET DEFAULT false;",
            reverse_sql="ALTER TABLE submissions_submission ALTER COLUMN is_correct DROP DEFAULT;",
        ),
    ]
