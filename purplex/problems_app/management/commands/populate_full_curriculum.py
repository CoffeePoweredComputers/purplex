from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from purplex.problems_app.models import Problem, ProblemSet, ProblemCategory, TestCase, ProblemSetMembership, ProblemHint

class Command(BaseCommand):
    help = 'Populate FULL 98-problem curriculum across 6 courses'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of ALL curriculum data (delete existing)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('🚀 DEPLOYING FULL CURRICULUM - 98 PROBLEMS! 🚀\n'))
        
        if options['force']:
            self.stdout.write('Clearing ALL existing curriculum data...')
            Problem.objects.all().delete()
            ProblemCategory.objects.all().delete()
            ProblemSet.objects.all().delete()
        
        # Get or create instructors
        instructor_cs, _ = User.objects.get_or_create(
            username='instructor_cs',
            defaults={'email': 'instructor_cs@purplex.com', 'is_staff': True}
        )
        instructor_ds, _ = User.objects.get_or_create(
            username='instructor_ds',
            defaults={'email': 'instructor_ds@purplex.com', 'is_staff': True}
        )
        
        # Import and run each agent's creation
        self.stdout.write('\n📦 Creating Problems 1-3 (POC)...')
        from purplex.problems_app.management.commands.populate_curriculum_poc import Command as POCCommand
        poc = POCCommand()
        poc.handle(force=True)
        
        self.stdout.write('\n📦 Integrating Agent outputs (Problems 4-98)...')
        self.stdout.write('⚠️ NOTE: Agent outputs are standalone scripts, merging inline...\n')
        
        # Execute each agent script
        import subprocess
        agent_scripts = [
            '/tmp/agent_1a_output.py',
            '/tmp/agent_1b_output.py', 
            '/tmp/agent_1c_output.py',
            '/tmp/agent_2a_output.py',
            '/tmp/agent_2b_output.py',
            '/tmp/agent_2c_output.py',
            '/tmp/agent_3a_output.py',
            '/tmp/agent_3b_output.py',
            '/tmp/agent_4a_output.py',
            '/tmp/agent_4b_output.py',
            '/tmp/agent_5a_output.py',
            '/tmp/agent_5b_output.py',
        ]
        
        for i, script in enumerate(agent_scripts, 1):
            self.stdout.write(f'  Agent {i}/12: {script.split("/")[-1]}')
            # Copy to commands directory temporarily and execute
            import shutil
            import os
            basename = os.path.basename(script)
            temp_cmd = f'/app/purplex/problems_app/management/commands/temp_{basename}'
            shutil.copy(script, temp_cmd)
            
            # Execute via Django management command
            from django.core.management import call_command
            cmd_name = f'temp_{basename}'.replace('.py', '')
            try:
                call_command(cmd_name, force=True, stdout=self.stdout)
                self.stdout.write(self.style.SUCCESS(f'    ✅ Completed'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'    ❌ Error: {e}'))
            finally:
                # Cleanup
                if os.path.exists(temp_cmd):
                    os.remove(temp_cmd)
        
        # Final summary
        self.stdout.write(self.style.SUCCESS('\n\n🎉 FULL CURRICULUM DEPLOYMENT COMPLETE! 🎉\n'))
        self.stdout.write(f'✅ Total Problems: {Problem.objects.count()}')
        self.stdout.write(f'✅ Total Test Cases: {TestCase.objects.count()}')
        self.stdout.write(f'✅ Total Hints: {ProblemHint.objects.count()}')
        self.stdout.write(f'✅ Total Problem Sets: {ProblemSet.objects.count()}')
        self.stdout.write(f'✅ Total Categories: {ProblemCategory.objects.count()}')
