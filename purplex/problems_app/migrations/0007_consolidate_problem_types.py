"""
Migration to consolidate problem types to EiPL only.

This migration:
1. Converts any existing 'function_redefinition' problems to 'eipl'
2. Updates the problem_type field choices to only include 'eipl'

Background: The function_redefinition problem type was implemented but never
actually used in the frontend. This migration removes dead code and simplifies
the system to focus on the EiPL activity type.
"""

from django.db import migrations, models


def convert_function_redefinition_to_eipl(apps, schema_editor):
    """Convert any function_redefinition problems to eipl."""
    Problem = apps.get_model("problems_app", "Problem")
    updated = Problem.objects.filter(problem_type="function_redefinition").update(
        problem_type="eipl"
    )
    if updated:
        print(f"\n  Converted {updated} function_redefinition problem(s) to eipl")


def noop(apps, schema_editor):
    """Reverse migration is a no-op - data is already converted."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("problems_app", "0006_require_function_signature"),
    ]

    operations = [
        # First, convert any existing function_redefinition problems to eipl
        migrations.RunPython(convert_function_redefinition_to_eipl, noop),
        # Then, update the field to only allow 'eipl' as a choice
        migrations.AlterField(
            model_name="problem",
            name="problem_type",
            field=models.CharField(
                choices=[("eipl", "Explain in Plain Language (EiPL)")],
                default="eipl",
                help_text="Activity type for this problem. Currently only EiPL is supported.",
                max_length=20,
            ),
        ),
    ]
