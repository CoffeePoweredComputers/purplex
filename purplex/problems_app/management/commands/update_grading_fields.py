"""
Management command to update existing records with new grading fields.
This migrates data from legacy fields to the new grading system.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from purplex.problems_app.models import Problem, UserProgress
from purplex.submissions.models import Submission
from purplex.submissions.grading_service import GradingService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Update existing records with new grading fields based on GRADING_PIPELINE.md'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making changes to the database',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('Running in dry-run mode - no changes will be saved'))

        # Update Problem records
        self.stdout.write('Updating Problem records...')
        problems_updated = 0

        for problem in Problem.objects.all():
            updated = False

            # Set segmentation_threshold from JSON config if not already set
            if problem.segmentation_threshold == 2 and problem.segmentation_config:
                config_threshold = problem.segmentation_config.get('threshold')
                if config_threshold and config_threshold != 2:
                    problem.segmentation_threshold = config_threshold
                    updated = True
                    self.stdout.write(f'  {problem.slug}: threshold {2} -> {config_threshold}')

            # Set requires_highlevel_comprehension based on problem type and config
            if problem.problem_type == 'eipl':
                # Check if segmentation is disabled in config
                if problem.segmentation_config.get('enabled') == False:
                    problem.requires_highlevel_comprehension = False
                    updated = True
                    self.stdout.write(f'  {problem.slug}: highlevel requirement disabled')

            if updated and not dry_run:
                problem.save()
                problems_updated += 1

        self.stdout.write(self.style.SUCCESS(f'Updated {problems_updated} Problem records'))

        # Update Submission records
        self.stdout.write('\nUpdating Submission records...')
        submissions_updated = 0

        with transaction.atomic():
            for submission in Submission.objects.select_related('problem').all():
                updated = False

                # Set is_correct based on passed_all_tests
                if submission.is_correct != submission.passed_all_tests:
                    submission.is_correct = submission.passed_all_tests
                    updated = True

                # Set comprehension_level for EiPL submissions with segmentation
                if submission.submission_type == 'eipl' and hasattr(submission, 'segmentation'):
                    segmentation = submission.segmentation
                    if segmentation.comprehension_level == 'relational':
                        new_level = 'high-level'
                    elif segmentation.comprehension_level == 'multi_structural':
                        new_level = 'low-level'
                    else:
                        new_level = 'not_evaluated'

                    if submission.comprehension_level != new_level:
                        submission.comprehension_level = new_level
                        updated = True
                        self.stdout.write(f'  Submission {submission.submission_id}: {segmentation.comprehension_level} -> {new_level}')

                if updated and not dry_run:
                    submission.save()
                    submissions_updated += 1

        self.stdout.write(self.style.SUCCESS(f'Updated {submissions_updated} Submission records'))

        # Update UserProgress records
        self.stdout.write('\nUpdating UserProgress records...')
        progress_updated = 0

        with transaction.atomic():
            for progress in UserProgress.objects.select_related('problem', 'user').all():
                # Get the best submission for this progress
                best_submission = Submission.objects.filter(
                    user=progress.user,
                    problem=progress.problem,
                    problem_set=progress.problem_set,
                    course=progress.course
                ).order_by('-score', '-submitted_at').first()

                if best_submission:
                    # Calculate grade using GradingService
                    grade = GradingService.calculate_grade(best_submission)

                    if progress.grade != grade:
                        old_grade = progress.grade
                        progress.grade = grade

                        if not dry_run:
                            progress.save()
                            progress_updated += 1

                        self.stdout.write(
                            f'  {progress.user.username} - {progress.problem.slug}: '
                            f'{old_grade} -> {grade}'
                        )

        self.stdout.write(self.style.SUCCESS(f'Updated {progress_updated} UserProgress records'))

        if dry_run:
            self.stdout.write(self.style.WARNING('\nDry run complete - no changes were saved'))
        else:
            self.stdout.write(self.style.SUCCESS('\nAll records have been updated successfully!'))