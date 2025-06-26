# Generated manually for submission tracking system redesign

from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ('submissions_app', '0005_add_problem_set_to_submission'),
        ('problems_app', '0012_courseenrollment_courseproblemset_problemset_version_and_more'),
    ]

    operations = [
        # Add new fields to PromptSubmission
        migrations.AddField(
            model_name='promptsubmission',
            name='course',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='submissions', to='problems_app.course'),
        ),
        migrations.AddField(
            model_name='promptsubmission',
            name='code_variations',
            field=models.JSONField(default=list, help_text='List of generated code variations'),
        ),
        migrations.AddField(
            model_name='promptsubmission',
            name='test_results',
            field=models.JSONField(default=list, help_text='Test results for each variation'),
        ),
        migrations.AddField(
            model_name='promptsubmission',
            name='passing_variations',
            field=models.IntegerField(default=0, help_text='Number of variations that passed all tests'),
        ),
        migrations.AddField(
            model_name='promptsubmission',
            name='total_variations',
            field=models.IntegerField(default=0, help_text='Total number of variations generated'),
        ),
        
        # Rename time to submitted_at (handle manually to avoid prompt)
        migrations.RenameField(
            model_name='promptsubmission',
            old_name='time',
            new_name='submitted_at',
        ),
        
        # Update related_name for existing fields
        migrations.AlterField(
            model_name='promptsubmission',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='submissions', to='auth.user'),
        ),
        migrations.AlterField(
            model_name='promptsubmission',
            name='problem',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='submissions', to='problems_app.problem'),
        ),
        migrations.AlterField(
            model_name='promptsubmission',
            name='problem_set',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='submissions', to='problems_app.problemset'),
        ),
        migrations.AlterField(
            model_name='promptsubmission',
            name='score',
            field=models.IntegerField(default=0),
        ),
        
        # Add indexes for performance
        migrations.AddIndex(
            model_name='promptsubmission',
            index=models.Index(fields=['user', 'problem', 'course', '-submitted_at'], name='submissions_user_id_87c5f5_idx'),
        ),
        migrations.AddIndex(
            model_name='promptsubmission',
            index=models.Index(fields=['user', 'problem_set', 'course', '-submitted_at'], name='submissions_user_id_8a9d12_idx'),
        ),
        migrations.AddIndex(
            model_name='promptsubmission',
            index=models.Index(fields=['course', 'problem_set', 'problem', '-score'], name='submissions_course__f4c5b3_idx'),
        ),
        
        # Update Meta options
        migrations.AlterModelOptions(
            name='promptsubmission',
            options={'ordering': ['-submitted_at']},
        ),
        
        # Remove old fields (these can be removed after data migration)
        # Commenting out for safety - run these in a separate migration after verifying data
        # migrations.RemoveField(
        #     model_name='promptsubmission',
        #     name='firebase_uid',
        # ),
        # migrations.RemoveField(
        #     model_name='promptsubmission',
        #     name='submitted_by',
        # ),
        # migrations.RemoveField(
        #     model_name='promptsubmission',
        #     name='user_solution',
        # ),
        # migrations.RemoveField(
        #     model_name='promptsubmission',
        #     name='feedback',
        # ),
        # migrations.RemoveField(
        #     model_name='promptsubmission',
        #     name='passed_test_ids',
        # ),
    ]