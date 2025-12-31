# Generated manually for claim_predicate field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("problems_app", "0021_add_description_to_problem"),
    ]

    operations = [
        migrations.AddField(
            model_name="refuteproblem",
            name="claim_predicate",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Python expression that's True when claim holds (e.g., 'result > 0'). "
                "Available variables: result, and all input arguments.",
            ),
        ),
    ]
