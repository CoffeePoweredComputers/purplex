# Generated migration for performance indexes

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("problems_app", "0002_add_grading_fields"),
    ]

    operations = [
        # Add index for UserProgress
        migrations.AddIndex(
            model_name="userprogress",
            index=models.Index(
                fields=["user", "problem", "course"], name="idx_user_progress_lookup"
            ),
        ),
        migrations.AddIndex(
            model_name="userprogress",
            index=models.Index(
                fields=["user", "problem_set"], name="idx_user_progress_set"
            ),
        ),
        # Add index for CourseEnrollment
        migrations.AddIndex(
            model_name="courseenrollment",
            index=models.Index(fields=["user", "course"], name="idx_enrollment_lookup"),
        ),
    ]
