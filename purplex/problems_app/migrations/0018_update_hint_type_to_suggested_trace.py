# Generated migration to update input_suggestion to suggested_trace

from django.db import migrations


def update_hint_types(apps, schema_editor):
    """Update existing input_suggestion hints to suggested_trace"""
    ProblemHint = apps.get_model('problems_app', 'ProblemHint')
    
    # Update hint_type from input_suggestion to suggested_trace
    hints_to_update = ProblemHint.objects.filter(hint_type='input_suggestion')
    for hint in hints_to_update:
        hint.hint_type = 'suggested_trace'
        # Convert old content format to new format
        old_content = hint.content or {}
        hint.content = {
            'suggested_call': '',  # Will need to be filled manually
            'explanation': old_content.get('instructions', '')
        }
        hint.save()


def reverse_hint_types(apps, schema_editor):
    """Reverse operation - update suggested_trace back to input_suggestion"""
    ProblemHint = apps.get_model('problems_app', 'ProblemHint')
    
    hints_to_revert = ProblemHint.objects.filter(hint_type='suggested_trace')
    for hint in hints_to_revert:
        hint.hint_type = 'input_suggestion'
        # Convert back to old format
        old_content = hint.content or {}
        hint.content = {
            'test_cases': [],
            'instructions': old_content.get('explanation', '')
        }
        hint.save()


class Migration(migrations.Migration):

    dependencies = [
        ('problems_app', '0017_problemhint'),
    ]

    operations = [
        migrations.RunPython(update_hint_types, reverse_hint_types),
    ]