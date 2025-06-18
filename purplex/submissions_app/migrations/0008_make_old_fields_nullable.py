# Migration to make old fields nullable before removal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('submissions_app', '0007_migrate_submission_data'),
    ]

    operations = [
        # Make old fields nullable so they don't interfere with new submissions
        migrations.AlterField(
            model_name='promptsubmission',
            name='user_solution',
            field=models.JSONField(default=dict, blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='promptsubmission',
            name='feedback',
            field=models.TextField(blank=True, null=True, help_text="Detailed feedback from test results"),
        ),
        migrations.AlterField(
            model_name='promptsubmission',
            name='passed_test_ids',
            field=models.JSONField(default=list, blank=True, null=True, help_text="IDs of test cases that passed"),
        ),
        migrations.AlterField(
            model_name='promptsubmission',
            name='firebase_uid',
            field=models.CharField(max_length=255, blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='promptsubmission',
            name='submitted_by',
            field=models.CharField(max_length=255, blank=True, null=True, help_text="Username of the person who submitted this solution"),
        ),
    ]