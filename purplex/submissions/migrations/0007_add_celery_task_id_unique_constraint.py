# Generated manually for celery idempotency fix

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("submissions", "0006_add_mcq_submission_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="submission",
            name="celery_task_id",
            field=models.CharField(max_length=255, null=True, blank=True, unique=True),
        ),
    ]
