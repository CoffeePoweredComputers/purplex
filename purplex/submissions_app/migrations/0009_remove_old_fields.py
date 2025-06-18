# Migration to remove old fields after successful data migration

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('submissions_app', '0008_make_old_fields_nullable'),
    ]

    operations = [
        # Remove old fields that are no longer needed
        migrations.RemoveField(
            model_name='promptsubmission',
            name='firebase_uid',
        ),
        migrations.RemoveField(
            model_name='promptsubmission',
            name='submitted_by',
        ),
        migrations.RemoveField(
            model_name='promptsubmission',
            name='user_solution',
        ),
        migrations.RemoveField(
            model_name='promptsubmission',
            name='feedback',
        ),
        migrations.RemoveField(
            model_name='promptsubmission',
            name='passed_test_ids',
        ),
    ]