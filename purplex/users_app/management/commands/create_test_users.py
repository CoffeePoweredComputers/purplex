"""
Management command to create test users for development environment.
This command creates predefined test users that match the mock Firebase configuration.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from purplex.users_app.models import UserProfile
from purplex.config.environment import config


class Command(BaseCommand):
    help = 'Creates test users for development environment'
    
    # Test users matching mock_firebase.py
    TEST_USERS = [
        {
            'username': 'admin',
            'email': 'admin@test.local',
            'first_name': 'Test',
            'last_name': 'Admin',
            'is_staff': True,
            'is_superuser': True,
            'role': 'admin',
            'firebase_uid': 'mock-uid-admin'
        },
        {
            'username': 'instructor',
            'email': 'instructor@test.local',
            'first_name': 'Test',
            'last_name': 'Instructor',
            'is_staff': True,
            'is_superuser': False,
            'role': 'instructor',
            'firebase_uid': 'mock-uid-instructor'
        },
        {
            'username': 'student',
            'email': 'student@test.local',
            'first_name': 'Test',
            'last_name': 'Student',
            'is_staff': False,
            'is_superuser': False,
            'role': 'user',
            'firebase_uid': 'mock-uid-student'
        },
        {
            'username': 'student2',
            'email': 'student2@test.local',
            'first_name': 'Test',
            'last_name': 'Student2',
            'is_staff': False,
            'is_superuser': False,
            'role': 'user',
            'firebase_uid': 'mock-uid-student2'
        }
    ]
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation even in non-development environment',
        )
        parser.add_argument(
            '--password',
            type=str,
            default='testpass123',
            help='Password for test users (default: testpass123)',
        )
    
    def handle(self, *args, **options):
        # Check environment
        if not config.is_development and not options['force']:
            self.stdout.write(
                self.style.ERROR(
                    'Test users can only be created in development environment.\n'
                    'Use --force to override this check (not recommended).'
                )
            )
            return
        
        if not config.is_development:
            self.stdout.write(
                self.style.WARNING(
                    'WARNING: Creating test users in non-development environment!'
                )
            )
        
        password = options['password']
        created_count = 0
        updated_count = 0
        
        for user_data in self.TEST_USERS:
            # Check if user exists
            try:
                user = User.objects.get(username=user_data['username'])
                # Update existing user
                user.email = user_data['email']
                user.first_name = user_data['first_name']
                user.last_name = user_data['last_name']
                user.is_staff = user_data['is_staff']
                user.is_superuser = user_data['is_superuser']
                user.set_password(password)
                user.save()
                
                action = 'Updated'
                updated_count += 1
                
            except User.DoesNotExist:
                # Create new user
                user = User.objects.create_user(
                    username=user_data['username'],
                    email=user_data['email'],
                    password=password,
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    is_staff=user_data['is_staff'],
                    is_superuser=user_data['is_superuser']
                )
                action = 'Created'
                created_count += 1
            
            # Create or update UserProfile
            user_profile, profile_created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'firebase_uid': user_data['firebase_uid'],
                    'role': user_data['role']
                }
            )
            
            if not profile_created:
                # Update existing profile
                user_profile.firebase_uid = user_data['firebase_uid']
                user_profile.role = user_data['role']
                user_profile.save()
            
            self.stdout.write(
                f"{action}: {user.username} "
                f"(email: {user.email}, role: {user_data['role']}, "
                f"staff: {user.is_staff}, superuser: {user.is_superuser})"
            )
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\nTest users ready!\n'
                f'Created: {created_count}, Updated: {updated_count}\n'
                f'Password for all users: {password}\n'
                f'\nYou can now log in with:\n'
                f'  Admin: admin@test.local / {password}\n'
                f'  Instructor: instructor@test.local / {password}\n'
                f'  Student: student@test.local / {password}'
            )
        )
        
        # Additional setup in development
        if config.is_development:
            self._create_sample_data()
    
    def _create_sample_data(self):
        """Create sample courses and enrollments for testing"""
        from purplex.problems_app.models import Course, CourseEnrollment
        
        # Get users
        try:
            instructor = User.objects.get(username='instructor')
            student1 = User.objects.get(username='student')
            student2 = User.objects.get(username='student2')
        except User.DoesNotExist:
            return
        
        # Create a sample course
        course, created = Course.objects.get_or_create(
            id='CS101-2024',
            defaults={
                'name': 'Introduction to Programming',
                'description': 'Learn the basics of programming with Python',
                'instructor': instructor,
                'enrollment_code': 'CS101TEST',
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write(f'Created sample course: {course.name}')
            
            # Enroll students
            CourseEnrollment.objects.get_or_create(
                user=student1,
                course=course,
                defaults={'is_active': True}
            )
            CourseEnrollment.objects.get_or_create(
                user=student2,
                course=course,
                defaults={'is_active': True}
            )
            
            self.stdout.write('Enrolled students in sample course')