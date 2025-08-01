# Generated manually to convert transitional to multi_structural

from django.db import migrations

def convert_transitional_to_multi_structural(apps, schema_editor):
    """Convert all 'transitional' comprehension levels to 'multi_structural'"""
    SegmentationResult = apps.get_model('submissions_app', 'SegmentationResult')
    SegmentationResult.objects.filter(comprehension_level='transitional').update(
        comprehension_level='multi_structural'
    )

def reverse_conversion(apps, schema_editor):
    """Reverse operation - not really reversible but required"""
    pass  # Cannot meaningfully reverse this

class Migration(migrations.Migration):

    dependencies = [
        ('submissions_app', '0012_remove_transitional_comprehension'),
    ]

    operations = [
        migrations.RunPython(
            convert_transitional_to_multi_structural,
            reverse_conversion,
        ),
    ]