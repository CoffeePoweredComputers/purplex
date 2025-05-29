# Generated manually to remove time_limit and estimated_time fields

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('problems_app', '0009_rename_attempted_to_partially_complete'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='problem',
            name='estimated_time',
        ),
        migrations.RemoveField(
            model_name='problem',
            name='time_limit',
        ),
    ]