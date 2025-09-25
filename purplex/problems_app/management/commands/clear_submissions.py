"""
Django management command to clear all submission data.
Safely removes all submissions, test results, progress tracking, and related data
while preserving the core educational structure (users, problems, courses).
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth.models import User
from django.utils import timezone

from purplex.problems_app.models import (
    UserProgress, UserProblemSetProgress, ProgressSnapshot
)
from purplex.submissions.models import (
    Submission, TestExecution, HintActivation, CodeVariation,
    SegmentationAnalysis, SubmissionFeedback
)


class Command(BaseCommand):
    help = 'Clear all submission data while preserving core educational structure'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting anything'
        )
        parser.add_argument(
            '--no-input',
            action='store_true',
            help='Skip confirmation prompts (for automation)'
        )
        parser.add_argument(
            '--preserve-progress',
            action='store_true',
            help='Keep progress tracking but clear submission records'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        no_input = options['no_input']
        preserve_progress = options['preserve_progress']

        self.stdout.write(
            self.style.WARNING('🧹 Submission Clearing Tool')
        )

        if dry_run:
            self.stdout.write(
                self.style.NOTICE('Running in DRY-RUN mode - no data will be deleted')
            )

        # Get counts before deletion
        counts = self._get_data_counts()

        # Display what will be affected
        self._display_summary(counts, preserve_progress)

        if not dry_run and not no_input:
            confirm = input('\nAre you sure you want to proceed? Type "yes" to confirm: ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Operation cancelled.'))
                return

        # Perform the deletion
        try:
            with transaction.atomic():
                deleted_counts = self._clear_submissions(dry_run, preserve_progress)

                if dry_run:
                    self.stdout.write(
                        self.style.SUCCESS('\n✅ DRY-RUN completed. No data was actually deleted.')
                    )
                    # Rollback transaction in dry-run mode
                    transaction.set_rollback(True)
                else:
                    self._display_results(deleted_counts)
                    self.stdout.write(
                        self.style.SUCCESS('\n✅ All submission data cleared successfully!')
                    )

        except Exception as e:
            raise CommandError(f'Error clearing submissions: {e}')

    def _get_data_counts(self):
        """Get counts of all data that will be affected"""
        return {
            'submissions': Submission.objects.count(),
            'test_executions': TestExecution.objects.count(),
            'hint_activations': HintActivation.objects.count(),
            'code_variations': CodeVariation.objects.count(),
            'segmentation_analyses': SegmentationAnalysis.objects.count(),
            'submission_feedback': SubmissionFeedback.objects.count(),
            'user_progress': UserProgress.objects.count(),
            'problem_set_progress': UserProblemSetProgress.objects.count(),
            'progress_snapshots': ProgressSnapshot.objects.count(),
            'users': User.objects.count()
        }

    def _display_summary(self, counts, preserve_progress):
        """Display what will be affected"""
        self.stdout.write('\n📊 Data Summary:')
        self.stdout.write(f'  • Submissions: {counts["submissions"]}')
        self.stdout.write(f'  • Test Executions: {counts["test_executions"]}')
        self.stdout.write(f'  • Hint Activations: {counts["hint_activations"]}')
        self.stdout.write(f'  • Code Variations: {counts["code_variations"]}')
        self.stdout.write(f'  • Segmentation Analyses: {counts["segmentation_analyses"]}')
        self.stdout.write(f'  • Submission Feedback: {counts["submission_feedback"]}')

        if not preserve_progress:
            self.stdout.write(f'  • User Progress Records: {counts["user_progress"]}')
            self.stdout.write(f'  • Problem Set Progress: {counts["problem_set_progress"]}')
            self.stdout.write(f'  • Progress Snapshots: {counts["progress_snapshots"]}')
        else:
            self.stdout.write('  • Progress data will be PRESERVED')

        self.stdout.write(f'\n👥 Users will be preserved: {counts["users"]}')
        self.stdout.write('🎯 Problems, courses, and problem sets will be preserved')

    def _clear_submissions(self, dry_run, preserve_progress):
        """Clear submission data in the correct dependency order"""
        deleted_counts = {}

        # Delete in dependency order (children first, then parents)

        # 1. Submission Feedback
        if dry_run:
            count = SubmissionFeedback.objects.count()
        else:
            count, _ = SubmissionFeedback.objects.all().delete()
        deleted_counts['submission_feedback'] = count
        self.stdout.write(f'  📝 Submission Feedback: {count}')

        # 2. Hint Activations
        if dry_run:
            count = HintActivation.objects.count()
        else:
            count, _ = HintActivation.objects.all().delete()
        deleted_counts['hint_activations'] = count
        self.stdout.write(f'  💡 Hint Activations: {count}')

        # 3. Test Executions
        if dry_run:
            count = TestExecution.objects.count()
        else:
            count, _ = TestExecution.objects.all().delete()
        deleted_counts['test_executions'] = count
        self.stdout.write(f'  🧪 Test Executions: {count}')

        # 4. Code Variations
        if dry_run:
            count = CodeVariation.objects.count()
        else:
            count, _ = CodeVariation.objects.all().delete()
        deleted_counts['code_variations'] = count
        self.stdout.write(f'  🔄 Code Variations: {count}')

        # 5. Segmentation Analyses
        if dry_run:
            count = SegmentationAnalysis.objects.count()
        else:
            count, _ = SegmentationAnalysis.objects.all().delete()
        deleted_counts['segmentation_analyses'] = count
        self.stdout.write(f'  🧠 Segmentation Analyses: {count}')

        # 6. Main Submissions
        if dry_run:
            count = Submission.objects.count()
        else:
            count, _ = Submission.objects.all().delete()
        deleted_counts['submissions'] = count
        self.stdout.write(f'  📋 Submissions: {count}')

        # 7. Progress data (if not preserving)
        if not preserve_progress:
            # Progress Snapshots
            if dry_run:
                count = ProgressSnapshot.objects.count()
            else:
                count, _ = ProgressSnapshot.objects.all().delete()
            deleted_counts['progress_snapshots'] = count
            self.stdout.write(f'  📸 Progress Snapshots: {count}')

            # User Problem Set Progress
            if dry_run:
                count = UserProblemSetProgress.objects.count()
            else:
                count, _ = UserProblemSetProgress.objects.all().delete()
            deleted_counts['problem_set_progress'] = count
            self.stdout.write(f'  📊 Problem Set Progress: {count}')

            # User Progress
            if dry_run:
                count = UserProgress.objects.count()
            else:
                count, _ = UserProgress.objects.all().delete()
            deleted_counts['user_progress'] = count
            self.stdout.write(f'  👤 User Progress: {count}')

        return deleted_counts

    def _display_results(self, deleted_counts):
        """Display final results"""
        total_deleted = sum(deleted_counts.values())
        self.stdout.write(f'\n📈 Summary: {total_deleted} records deleted')
        self.stdout.write('🎯 Core educational structure preserved')
        self.stdout.write(f'⏰ Completed at: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}')