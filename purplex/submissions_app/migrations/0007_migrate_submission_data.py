# Data migration to convert existing submission data to new format

from django.db import migrations
import json


def migrate_submission_data(apps, schema_editor):
    """Convert existing user_solution and feedback fields to new structured fields"""
    PromptSubmission = apps.get_model('submissions_app', 'PromptSubmission')
    
    for submission in PromptSubmission.objects.all():
        # Initialize new fields
        code_variations = []
        test_results = []
        passing_variations = 0
        
        # Try to parse user_solution field
        if submission.user_solution:
            try:
                if isinstance(submission.user_solution, str):
                    data = json.loads(submission.user_solution)
                else:
                    data = submission.user_solution
                
                code_variations = data.get('variations', [])
                test_results = data.get('results', [])
            except (json.JSONDecodeError, AttributeError):
                pass
        
        # Try to parse feedback field as backup
        if not code_variations and submission.feedback:
            try:
                if isinstance(submission.feedback, str) and submission.feedback.startswith('{'):
                    data = json.loads(submission.feedback)
                    code_variations = data.get('variations', [])
                    test_results = data.get('test_results', test_results)
                    passing_variations = data.get('passing_variations', 0)
                    submission.total_variations = data.get('total_variations', len(code_variations))
            except (json.JSONDecodeError, AttributeError):
                pass
        
        # Calculate passing variations if not provided
        if test_results and not passing_variations:
            for result_set in test_results:
                if isinstance(result_set, list) and all(test.get('pass', False) for test in result_set):
                    passing_variations += 1
        
        # Update submission with new fields
        submission.code_variations = code_variations
        submission.test_results = test_results
        submission.passing_variations = passing_variations
        submission.total_variations = len(code_variations) if code_variations else 0
        submission.save()


def reverse_migration(apps, schema_editor):
    """Reverse migration - restore data to old format"""
    PromptSubmission = apps.get_model('submissions_app', 'PromptSubmission')
    
    for submission in PromptSubmission.objects.all():
        # Restore user_solution field
        submission.user_solution = json.dumps({
            'prompt': submission.prompt,
            'variations': submission.code_variations,
            'results': submission.test_results
        })
        submission.save()


class Migration(migrations.Migration):

    dependencies = [
        ('submissions_app', '0006_submission_tracking_redesign'),
    ]

    operations = [
        migrations.RunPython(migrate_submission_data, reverse_migration),
    ]