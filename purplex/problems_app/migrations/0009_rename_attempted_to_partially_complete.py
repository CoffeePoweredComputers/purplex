# Generated manually for renaming attempted to partially complete

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("problems_app", "0008_add_performance_indexes"),
    ]

    operations = [
        migrations.RenameField(
            model_name="userproblemsetprogress",
            old_name="attempted_problems",
            new_name="partially_complete_problems",
        ),
    ]