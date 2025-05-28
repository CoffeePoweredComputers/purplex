import os
import yaml
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction
from purplex.problems_app.models import Problem

class Command(BaseCommand):
    help = 'Load problems into the database'

    def handle(self, *args, **kwargs):
        # Get the base directory of the project
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        problems_dir = os.path.join(base_dir, 'purplex', 'problems')
        
        if not os.path.exists(problems_dir):
            self.stdout.write(self.style.WARNING(f"Problems directory not found: {problems_dir}"))
            return

        # Collect all problem data first
        problems_to_create = []
        problems_to_update = []
        test_files_to_save = []
        
        # Get existing problems for comparison
        existing_problems = {p.qid: p for p in Problem.objects.all()}
        
        problem_dirs = [d for d in os.listdir(problems_dir) if os.path.isdir(os.path.join(problems_dir, d))]
        self.stdout.write(f"Found {len(problem_dirs)} problem directories to process")

        for problem_dir in problem_dirs:
            problem_path = os.path.join(problems_dir, problem_dir)
            
            meta_file = os.path.join(problem_path, 'meta.yaml')
            test_file = os.path.join(problem_path, 'tests.json')
            solution_file = os.path.join(problem_path, 'solution.py')
            
            # Skip if required files don't exist
            if not all(os.path.exists(f) for f in [meta_file, test_file, solution_file]):
                self.stdout.write(self.style.WARNING(f"Skipping {problem_dir}: missing required files"))
                continue

            try:
                # Read all data
                with open(meta_file) as f:
                    meta_data = yaml.safe_load(f)
                
                with open(solution_file) as f:
                    solution_content = f.read()
                
                qid = meta_data.get('qid')
                if not qid:
                    self.stdout.write(self.style.WARNING(f"Skipping {problem_dir}: no qid in meta.yaml"))
                    continue
                
                # Check if problem exists
                if qid in existing_problems:
                    # Update existing problem
                    problem = existing_problems[qid]
                    problem.title = meta_data.get('title', problem.title)
                    problem.description = meta_data.get('description', problem.description)
                    problem.solution = solution_content
                    problems_to_update.append(problem)
                    test_files_to_save.append((problem, test_file, qid))
                else:
                    # Create new problem
                    problem = Problem(
                        qid=qid,
                        title=meta_data.get('title', ''),
                        description=meta_data.get('description', ''),
                        solution=solution_content
                    )
                    problems_to_create.append(problem)
                    test_files_to_save.append((problem, test_file, qid))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing {problem_dir}: {str(e)}"))
                continue

        # Bulk operations in a transaction
        with transaction.atomic():
            # Bulk create new problems
            if problems_to_create:
                Problem.objects.bulk_create(problems_to_create)
                self.stdout.write(self.style.SUCCESS(f"Created {len(problems_to_create)} new problems"))
            
            # Bulk update existing problems
            if problems_to_update:
                Problem.objects.bulk_update(problems_to_update, ['title', 'description', 'solution'])
                self.stdout.write(self.style.SUCCESS(f"Updated {len(problems_to_update)} existing problems"))
            
            # Save test case files (still need individual saves for file fields)
            for problem, test_file, qid in test_files_to_save:
                if not problem.pk:
                    # For newly created problems, get the saved instance
                    problem = Problem.objects.get(qid=qid)
                
                with open(test_file, 'rb') as f:
                    problem.test_case_file.save(f"{qid}_tests.json", File(f), save=True)
        
        total_processed = len(problems_to_create) + len(problems_to_update)
        self.stdout.write(self.style.SUCCESS(f"Successfully processed {total_processed} problems"))