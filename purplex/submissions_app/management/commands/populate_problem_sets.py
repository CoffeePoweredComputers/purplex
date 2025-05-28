from django.core.management.base import BaseCommand
from purplex.submissions_app.models import PromptSubmission
from purplex.problems_app.models import ProblemSetMembership


class Command(BaseCommand):
    help = 'Populate missing problem_set associations for existing submissions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        def find_primary_problem_set(problem):
            """Find the best problem set for a problem"""
            memberships = ProblemSetMembership.objects.filter(problem=problem).select_related('problem_set')
            
            if not memberships.exists():
                return None
            
            # Return the first problem set (could add logic for 'primary' set)
            return memberships.first().problem_set

        # Find submissions without problem_set
        null_submissions = PromptSubmission.objects.filter(problem_set__isnull=True)
        total_null = null_submissions.count()
        
        self.stdout.write(f"Found {total_null} submissions without problem_set association")
        
        if total_null == 0:
            self.stdout.write(self.style.SUCCESS("All submissions already have problem_set associations!"))
            return

        updated_count = 0
        skipped_count = 0

        for submission in null_submissions:
            primary_set = find_primary_problem_set(submission.problem)
            
            if primary_set:
                if dry_run:
                    self.stdout.write(
                        f"Would update submission {submission.id}: "
                        f"{submission.problem.title} -> {primary_set.title}"
                    )
                else:
                    submission.problem_set = primary_set
                    submission.save()
                    self.stdout.write(
                        f"Updated submission {submission.id}: "
                        f"{submission.problem.title} -> {primary_set.title}"
                    )
                updated_count += 1
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipped submission {submission.id}: "
                        f"Problem '{submission.problem.title}' not found in any problem set"
                    )
                )
                skipped_count += 1

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would update {updated_count} submissions, "
                    f"skip {skipped_count} submissions"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Updated {updated_count} submissions with problem set associations"
                )
            )
            if skipped_count > 0:
                self.stdout.write(
                    self.style.WARNING(f"Skipped {skipped_count} submissions")
                )

        # Show final stats
        remaining_null = PromptSubmission.objects.filter(problem_set__isnull=True).count()
        if not dry_run:
            self.stdout.write(f"Submissions still with null problem_set: {remaining_null}")