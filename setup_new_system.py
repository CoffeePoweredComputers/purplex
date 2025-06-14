#!/usr/bin/env python3
"""
Setup script for the new problem creation system.
Run this script to migrate from the old file-based system to the new database-native system.
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'purplex.settings')
django.setup()

from django.core.management import execute_from_command_line
from django.core.management.color import make_style
from django.db import connection

style = make_style('ERROR')

def print_step(step, description):
    print(f"\n{style.SUCCESS('='*60)}")
    print(f"{style.SUCCESS(f'STEP {step}: {description}')}")
    print(f"{style.SUCCESS('='*60)}")

def print_success(message):
    print(f"{style.SUCCESS('✓')} {message}")

def print_error(message):
    print(f"{style.ERROR('✗')} {message}")

def print_warning(message):
    print(f"{style.WARNING('⚠')} {message}")

def main():
    print(f"{style.SUCCESS('🚀 Setting up new Problem Creation System')}")
    print(f"{style.NOTICE('This will migrate from file-based to database-native system')}")
    
    try:
        # Step 1: Run migrations
        print_step(1, "Running Database Migrations")
        execute_from_command_line(['manage.py', 'migrate'])
        print_success("Database migrations completed")
        
        # Step 2: Populate sample data
        print_step(2, "Creating Sample Data")
        execute_from_command_line(['manage.py', 'populate_sample_data'])
        print_success("Sample data created")
        
        # Step 3: Create superuser if needed
        print_step(3, "Checking Admin User")
        from django.contrib.auth.models import User
        if not User.objects.filter(is_superuser=True).exists():
            print_warning("No superuser found. Creating admin user...")
            print("Please create an admin user:")
            execute_from_command_line(['manage.py', 'createsuperuser'])
        else:
            print_success("Admin user already exists")
        
        # Step 4: Collect static files
        print_step(4, "Collecting Static Files")
        execute_from_command_line(['manage.py', 'collectstatic', '--noinput'])
        print_success("Static files collected")
        
        # Step 5: Verify setup
        print_step(5, "Verifying Setup")
        from purplex.problems_app.models import Problem, ProblemCategory, ProblemSet, TestCase
        
        problem_count = Problem.objects.count()
        category_count = ProblemCategory.objects.count()
        set_count = ProblemSet.objects.count()
        test_count = TestCase.objects.count()
        
        print_success(f"Found {problem_count} problems")
        print_success(f"Found {category_count} categories")
        print_success(f"Found {set_count} problem sets")
        print_success(f"Found {test_count} test cases")
        
        if problem_count > 0:
            print_success("Database setup verified!")
        else:
            print_warning("No problems found. You may need to create some manually.")
        
        # Step 6: Final instructions
        print_step(6, "Setup Complete!")
        print(f"{style.SUCCESS('✨ New Problem Creation System is ready!')}")
        print(f"\n{style.NOTICE('Next steps:')}")
        print(f"1. Start the development server: python manage.py runserver")
        print(f"2. Visit the admin interface: http://localhost:8000/admin/")
        print(f"3. Create new problems using the rich web interface")
        print(f"4. Use the API endpoints for frontend integration")
        
        print(f"\n{style.NOTICE('Key improvements:')}")
        print("• No more file duplication (was 605 files, now database-native)")
        print("• Live testing of solutions as you write them")
        print("• Rich admin interface with validation")
        print("• AI-powered test case generation")
        print("• Version control and collaboration features")
        print("• Proper categorization and tagging")
        
        print(f"\n{style.NOTICE('API Endpoints:')}")
        print("• GET /api/admin/problems/ - List all problems")
        print("• POST /api/admin/problems/ - Create new problem")
        print("• PUT /api/admin/problems/<slug>/ - Update problem")
        print("• POST /api/admin/test-problem/ - Test solution")
        print("• POST /api/admin/generate-test-cases/ - AI generation")
        
    except Exception as e:
        print_error(f"Setup failed: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()