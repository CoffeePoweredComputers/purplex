import os
import yaml
from django.core.files import File
from django.core.management.base import BaseCommand
from purplex.problems_app.models import Problem

class Command(BaseCommand):
    help = 'Load problems into the database'

    def handle(self, *args, **kwargs):
        # Get the base directory of the project
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        problems_dir = os.path.join(base_dir, 'purplex', 'problems')

        for problem_dir in os.listdir(problems_dir):

            problem_path = os.path.join(problems_dir, problem_dir)

            if os.path.isdir(problem_path):
                meta_file = os.path.join(problem_path, 'meta.yaml')
                test_file = os.path.join(problem_path, 'tests.json')
                solution_file = os.path.join(problem_path, 'solution.py')

                with open(meta_file) as f:
                    meta_data = yaml.safe_load(f)


                problem = Problem(
                    qid=meta_data['qid'],
                    title=meta_data['title'],
                    description=meta_data['description']
                )

                # open the solution file
                with open(solution_file) as infile:
                    problem.solution = infile.read()

                problem.test_case_file.save(f"{meta_data['qid']}_tests.json", File(open(test_file, 'rb')))

                problem.save()
                self.stdout.write(self.style.SUCCESS(f"Successfully loaded {problem.qid}"))