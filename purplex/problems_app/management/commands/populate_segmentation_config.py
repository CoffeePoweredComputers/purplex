from django.core.management.base import BaseCommand
from django.db import transaction
from purplex.problems_app.models import Problem


class Command(BaseCommand):
    help = 'Populate segmentation configuration for existing EiPL problems'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--threshold',
            type=int,
            default=2,
            help='Default segmentation threshold (default: 2)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        threshold = options['threshold']
        
        # Default segmentation configuration
        default_config = {
            "enabled": True,
            "threshold": threshold,
            "show_feedback": True,
            "examples": {
                "good": {
                    "prompt": "This function sums all positive numbers in the array",
                    "segments": 1,
                    "level": "relational",
                    "explanation": "Describes the overall purpose in one clear statement"
                },
                "poor": {
                    "prompt": "First set sum to 0. Then loop through array. Check if each element is positive. If positive add to sum. Return sum.",
                    "segments": 5,
                    "level": "multi_structural", 
                    "explanation": "Lists each step of the implementation separately"
                }
            },
            "guidance": {
                "relational": "Excellent! Your response shows high-level understanding of the code's purpose.",
                "transitional": "Good start! Try to describe the overall goal in fewer segments.",
                "multi_structural": "Your response describes the steps well, but try to focus on the overall purpose instead of individual steps."
            }
        }

        # Find EiPL problems that need configuration
        problems_to_update = Problem.objects.filter(
            problem_type='eipl',
            segmentation_config__exact={}
        )

        if not problems_to_update.exists():
            self.stdout.write(
                self.style.SUCCESS('No EiPL problems need segmentation configuration updates.')
            )
            return

        self.stdout.write(f'Found {problems_to_update.count()} EiPL problems to update.')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))
            for problem in problems_to_update:
                self.stdout.write(f'  Would update: {problem.title} (slug: {problem.slug})')
            return

        # Update problems with default configuration
        with transaction.atomic():
            updated_count = 0
            for problem in problems_to_update:
                problem.segmentation_config = default_config.copy()
                problem.save(update_fields=['segmentation_config'])
                updated_count += 1
                
                self.stdout.write(f'  ✓ Updated: {problem.title}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated segmentation configuration for {updated_count} problems.'
            )
        )
        
        # Show summary of what was configured
        self.stdout.write('\nConfiguration applied:')
        self.stdout.write(f'  - Enabled: {default_config["enabled"]}')
        self.stdout.write(f'  - Threshold: {default_config["threshold"]} segments')
        self.stdout.write(f'  - Show feedback: {default_config["show_feedback"]}')
        self.stdout.write(f'  - Examples: {len(default_config["examples"])} provided')