"""
Django management command to fix orphaned UserProgress records.

This command identifies and fixes UserProgress records that were created
without problem_set context when problems were added to problem sets after creation.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from purplex.problems_app.models import UserProgress, ProblemSetMembership
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fix orphaned UserProgress records that lack problem_set context'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without making changes',
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Only fix records for a specific username',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        username = options.get('user')

        self.stdout.write('Finding orphaned progress records...')

        # Find all UserProgress records without problem_set
        query = UserProgress.objects.filter(problem_set__isnull=True)

        if username:
            query = query.filter(user__username=username)

        orphaned_progress = query.select_related('user', 'problem')

        if not orphaned_progress.exists():
            self.stdout.write(self.style.SUCCESS('No orphaned progress records found!'))
            return

        self.stdout.write(f'Found {orphaned_progress.count()} orphaned progress records')

        fixed_count = 0
        merged_count = 0

        for progress in orphaned_progress:
            # Check if this problem belongs to any problem sets
            memberships = ProblemSetMembership.objects.filter(
                problem=progress.problem
            ).select_related('problem_set')

            if not memberships.exists():
                self.stdout.write(
                    f'  Problem {progress.problem.slug} is not in any problem sets, skipping'
                )
                continue

            # For each problem set membership, check if we need to fix/merge progress
            for membership in memberships:
                problem_set = membership.problem_set

                if dry_run:
                    # Check if there's already a progress record with problem_set
                    existing = UserProgress.objects.filter(
                        user=progress.user,
                        problem=progress.problem,
                        problem_set=problem_set,
                        course=progress.course
                    ).first()

                    if existing:
                        self.stdout.write(
                            f'  Would merge: {progress.user.username} - {progress.problem.slug} '
                            f'into existing record for problem set {problem_set.slug}'
                        )
                    else:
                        self.stdout.write(
                            f'  Would update: {progress.user.username} - {progress.problem.slug} '
                            f'to include problem set {problem_set.slug}'
                        )
                else:
                    with transaction.atomic():
                        # Check if there's already a progress record with problem_set
                        existing = UserProgress.objects.filter(
                            user=progress.user,
                            problem=progress.problem,
                            problem_set=problem_set,
                            course=progress.course
                        ).first()

                        if existing:
                            # Merge the orphaned record into the existing one
                            if progress.best_score > existing.best_score:
                                existing.best_score = progress.best_score

                            existing.attempts += progress.attempts

                            if progress.first_attempt and (
                                not existing.first_attempt or
                                progress.first_attempt < existing.first_attempt
                            ):
                                existing.first_attempt = progress.first_attempt

                            if progress.last_attempt and (
                                not existing.last_attempt or
                                progress.last_attempt > existing.last_attempt
                            ):
                                existing.last_attempt = progress.last_attempt

                            if progress.completed_at and not existing.completed_at:
                                existing.completed_at = progress.completed_at
                                existing.is_completed = True
                                existing.status = 'completed'

                            if progress.total_time_spent:
                                existing.total_time_spent = (
                                    existing.total_time_spent + progress.total_time_spent
                                    if existing.total_time_spent else progress.total_time_spent
                                )

                            existing.save()

                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'  ✓ Merged: {progress.user.username} - {progress.problem.slug} '
                                    f'into existing record for problem set {problem_set.slug}'
                                )
                            )
                            merged_count += 1

                            # We'll delete the orphaned record after processing all memberships
                        else:
                            # Update the orphaned record to include problem_set
                            # Create a copy with problem_set
                            new_progress = UserProgress.objects.create(
                                user=progress.user,
                                problem=progress.problem,
                                problem_set=problem_set,
                                course=progress.course,
                                problem_version=progress.problem_version,
                                attempts=progress.attempts,
                                best_score=progress.best_score,
                                average_score=progress.average_score,
                                status=progress.status,
                                is_completed=progress.is_completed,
                                completion_percentage=progress.completion_percentage,
                                first_attempt=progress.first_attempt,
                                last_attempt=progress.last_attempt,
                                completed_at=progress.completed_at,
                                total_time_spent=progress.total_time_spent,
                                hints_used=progress.hints_used,
                                days_to_complete=progress.days_to_complete
                            )

                            if hasattr(progress, 'grade'):
                                new_progress.grade = progress.grade
                                new_progress.save()

                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'  ✓ Created: {progress.user.username} - {progress.problem.slug} '
                                    f'with problem set {problem_set.slug}'
                                )
                            )
                            fixed_count += 1

            # After processing all memberships, delete the orphaned record (if not dry run)
            if not dry_run:
                progress.delete()
                self.stdout.write(
                    f'  Deleted orphaned record for {progress.user.username} - {progress.problem.slug}'
                )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\nDry run complete. Would fix {orphaned_progress.count()} orphaned records.'
                )
            )
            self.stdout.write('Run without --dry-run to apply fixes.')
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✅ Fixed {fixed_count} records and merged {merged_count} records!'
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'Deleted {orphaned_progress.count()} orphaned records.'
                )
            )