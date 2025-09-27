"""
Management command to fix requires_highlevel_comprehension field for existing EiPL problems.

This command addresses the issue where EiPL problems created through the admin interface
don't have the requires_highlevel_comprehension field properly set, which breaks
progress tracking and completion detection.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from purplex.problems_app.models import Problem


class Command(BaseCommand):
    help = 'Fix requires_highlevel_comprehension field for existing EiPL problems'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making actual changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))

        self.stdout.write('Checking EiPL problems for correct requires_highlevel_comprehension setting...')

        # Get all EiPL problems
        eipl_problems = Problem.objects.filter(problem_type='eipl')

        problems_to_fix = []
        problems_already_correct = []

        for problem in eipl_problems:
            # Check if segmentation is enabled in the config
            segmentation_enabled = problem.segmentation_config.get('enabled', True)

            # Determine what the field should be
            expected_value = segmentation_enabled

            # Check if it needs fixing
            if problem.requires_highlevel_comprehension != expected_value:
                problems_to_fix.append({
                    'problem': problem,
                    'current': problem.requires_highlevel_comprehension,
                    'expected': expected_value,
                    'segmentation_enabled': segmentation_enabled
                })
            else:
                problems_already_correct.append(problem)

        # Report findings
        self.stdout.write(f'\nFound {len(eipl_problems)} EiPL problems total')
        self.stdout.write(f'  - {len(problems_already_correct)} already correct')
        self.stdout.write(f'  - {len(problems_to_fix)} need fixing')

        if problems_to_fix:
            self.stdout.write('\nProblems that need fixing:')
            for item in problems_to_fix:
                problem = item['problem']
                self.stdout.write(
                    f'  {problem.slug}: "{problem.title}"'
                    f' (current: {item["current"]}, should be: {item["expected"]},'
                    f' segmentation_enabled: {item["segmentation_enabled"]})'
                )

        if problems_to_fix and not dry_run:
            self.stdout.write('\nFixing problems...')

            with transaction.atomic():
                for item in problems_to_fix:
                    problem = item['problem']
                    problem.requires_highlevel_comprehension = item['expected']
                    problem.save(update_fields=['requires_highlevel_comprehension'])

                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  Fixed: {problem.slug} - '
                            f'requires_highlevel_comprehension set to {item["expected"]}'
                        )
                    )

            self.stdout.write(self.style.SUCCESS(f'\nSuccessfully fixed {len(problems_to_fix)} problems'))
        elif problems_to_fix and dry_run:
            self.stdout.write(self.style.WARNING(f'\nDRY RUN: Would fix {len(problems_to_fix)} problems'))
        else:
            self.stdout.write(self.style.SUCCESS('\nNo problems need fixing!'))

        # Additional check: Report any non-EiPL problems that have requires_highlevel_comprehension=True
        non_eipl_with_flag = Problem.objects.filter(
            requires_highlevel_comprehension=True
        ).exclude(problem_type='eipl')

        if non_eipl_with_flag.exists():
            self.stdout.write(self.style.WARNING(
                f'\nWarning: Found {non_eipl_with_flag.count()} non-EiPL problems with '
                'requires_highlevel_comprehension=True (this may be incorrect):'
            ))
            for problem in non_eipl_with_flag[:5]:  # Show first 5
                self.stdout.write(f'  - {problem.slug} ({problem.problem_type})')
            if non_eipl_with_flag.count() > 5:
                self.stdout.write(f'  ... and {non_eipl_with_flag.count() - 5} more')