import os
import yaml
from django.core.management.base import BaseCommand
from purplex.models import ProblemSet, Problem

class Command(BaseCommand):
    help = 'Load problem sets into the database'

    def handle(self, *args, **kwargs):
        problemset_dirs = 'purplex/problemsets/'

        for problemset_dir in os.listdir(problemset_dirs):

            print(f"Loading: {problemset_dir}")

            problemset_file = os.path.join(problemset_dirs, problemset_dir, 'meta.yaml')
            if not os.path.exists(problemset_file):
                self.stdout.write(self.style.ERROR(f"Meta file does not exist for {problemset_dir}"))
                continue

            icon_file = os.path.join(problemset_dirs, problemset_dir, 'icon.jpg')
            if not os.path.exists(icon_file):
                self.stdout.write(self.style.ERROR(f"Icon file does not exist for {problemset_dir}"))
                continue

            with open(problemset_file, 'r') as f:
                problemset_data = yaml.safe_load(f)

            # if the problem doesn't exist ask if you want to replace it
            if ProblemSet.objects.filter(sid=problemset_data['sid']).exists():
                replace = input("This problem set already exists. Do you want to replace it? (y/n): ")
                if replace.lower() == 'y':
                    ProblemSet.objects.filter(sid=problemset_data['sid']).delete()
                else:
                    print("Skipping...")
                    continue

            problem_set = ProblemSet(
                sid=problemset_data['sid'], 
                title=problemset_data['title'],
                icon=icon_file
            )
            problem_set.save()

            for qid in problemset_data['problems']:
                try:
                    problem = Problem.objects.get(qid=qid)
                    problem_set.problems.add(problem)
                except Problem.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"Problem with QID {qid} does not exist"))
            
            problem_set.save()
            self.stdout.write(self.style.SUCCESS(f"Successfully loaded {problem_set.sid}"))
