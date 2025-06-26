# Generated manually for adding course context to progress tracking

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('problems_app', '0012_courseenrollment_courseproblemset_problemset_version_and_more'),
    ]

    operations = [
        # Add course field to UserProblemSetProgress
        migrations.AddField(
            model_name='userproblemsetprogress',
            name='course',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='problems_app.course'),
        ),
        
        # Update unique constraint to include course
        migrations.AlterUniqueTogether(
            name='userproblemsetprogress',
            unique_together={('user', 'problem_set', 'course')},
        ),
        
        # Add new indexes for course-based queries
        migrations.AddIndex(
            model_name='userproblemsetprogress',
            index=models.Index(fields=['user', 'course', '-last_activity'], name='problems_ap_user_id_course_last_idx'),
        ),
        migrations.AddIndex(
            model_name='userproblemsetprogress',
            index=models.Index(fields=['problem_set', 'course', '-completion_percentage'], name='problems_ap_problem_course_comp_idx'),
        ),
    ]