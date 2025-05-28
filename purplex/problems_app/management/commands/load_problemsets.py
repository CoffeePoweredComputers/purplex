import os
import yaml
from django.core.management.base import BaseCommand
from django.db import transaction
from django.core.files import File
from purplex.problems_app.models import ProblemSet, Problem, ProblemSetMembership

class Command(BaseCommand):
    help = 'Load problem sets into the database (optimized version)'

    def handle(self, *args, **kwargs):
        # Get the base directory of the project
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        problemset_dirs = os.path.join(base_dir, 'purplex', 'problemsets')
        
        if not os.path.exists(problemset_dirs):
            self.stdout.write(self.style.WARNING(f"Problem sets directory not found: {problemset_dirs}"))
            return

        # Collect all problemset data first
        problemsets_to_process = []
        
        # Get all existing problem sets by slug (since 'sid' field doesn't exist in model)
        existing_sets = {ps.slug: ps for ps in ProblemSet.objects.all()}
        
        # Cache all problems by slug for efficient lookup
        all_problems = {p.slug: p for p in Problem.objects.all()}
        
        problemset_list = [d for d in os.listdir(problemset_dirs) if os.path.isdir(os.path.join(problemset_dirs, d))]
        self.stdout.write(f"Found {len(problemset_list)} problem set directories to process")

        for problemset_dir in problemset_list:
            problemset_file = os.path.join(problemset_dirs, problemset_dir, 'meta.yaml')
            icon_file = os.path.join(problemset_dirs, problemset_dir, 'icon.jpg')
            
            if not os.path.exists(problemset_file):
                self.stdout.write(self.style.WARNING(f"Skipping {problemset_dir}: meta.yaml not found"))
                continue

            if not os.path.exists(icon_file):
                self.stdout.write(self.style.WARNING(f"Skipping {problemset_dir}: icon.jpg not found"))
                continue

            try:
                with open(problemset_file, 'r') as f:
                    problemset_data = yaml.safe_load(f)
                
                # Extract data - adapt to use slug instead of sid
                slug = problemset_data.get('sid', problemset_data.get('slug', problemset_dir))
                title = problemset_data.get('title', '')
                description = problemset_data.get('description', '')
                problem_slugs = problemset_data.get('problems', [])
                
                problemsets_to_process.append({
                    'slug': slug,
                    'title': title,
                    'description': description,
                    'icon_file': icon_file,
                    'problem_slugs': problem_slugs,
                    'exists': slug in existing_sets
                })
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing {problemset_dir}: {str(e)}"))
                continue

        # Process all problem sets in a transaction
        with transaction.atomic():
            created_count = 0
            updated_count = 0
            
            for ps_data in problemsets_to_process:
                if ps_data['exists']:
                    # Update existing problem set
                    problem_set = existing_sets[ps_data['slug']]
                    problem_set.title = ps_data['title']
                    problem_set.description = ps_data['description']
                    
                    # Update icon
                    with open(ps_data['icon_file'], 'rb') as f:
                        problem_set.icon.save(f'icon_{ps_data["slug"]}.jpg', File(f), save=False)
                    
                    problem_set.save()
                    
                    # Clear existing memberships
                    ProblemSetMembership.objects.filter(problem_set=problem_set).delete()
                    
                    updated_count += 1
                else:
                    # Create new problem set
                    problem_set = ProblemSet(
                        slug=ps_data['slug'],
                        title=ps_data['title'],
                        description=ps_data['description']
                    )
                    problem_set.save()
                    
                    # Save icon
                    with open(ps_data['icon_file'], 'rb') as f:
                        problem_set.icon.save(f'icon_{ps_data["slug"]}.jpg', File(f), save=True)
                    
                    created_count += 1
                
                # Add problems through membership (bulk create)
                memberships_to_create = []
                missing_problems = []
                
                for order, problem_slug in enumerate(ps_data['problem_slugs']):
                    if problem_slug in all_problems:
                        memberships_to_create.append(
                            ProblemSetMembership(
                                problem_set=problem_set,
                                problem=all_problems[problem_slug],
                                order=order
                            )
                        )
                    else:
                        missing_problems.append(problem_slug)
                
                # Bulk create memberships
                if memberships_to_create:
                    ProblemSetMembership.objects.bulk_create(memberships_to_create)
                
                # Report missing problems
                if missing_problems:
                    self.stdout.write(self.style.WARNING(
                        f"Problem set '{ps_data['slug']}': Problems not found: {', '.join(missing_problems)}"
                    ))
                
                self.stdout.write(self.style.SUCCESS(f"Successfully processed {ps_data['slug']}"))
        
        self.stdout.write(self.style.SUCCESS(
            f"Completed: {created_count} created, {updated_count} updated"
        ))