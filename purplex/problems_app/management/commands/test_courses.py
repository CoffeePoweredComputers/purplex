from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from purplex.problems_app.models import (
    Course,
    CourseEnrollment,
    CourseInstructor,
    CourseProblemSet,
    ProblemSet,
)
from purplex.users_app.models import UserProfile, UserRole


class Command(BaseCommand):
    help = "Test the course management system"

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS("=== Testing Course Management System ===")
        )

        # Get or create test users
        admin_user, _ = User.objects.get_or_create(
            username="test_admin",
            defaults={
                "email": "admin@test.com",
                "first_name": "Test",
                "last_name": "Admin",
            },
        )
        admin_profile, _ = UserProfile.objects.get_or_create(
            user=admin_user,
            defaults={"firebase_uid": "test_admin_uid", "role": UserRole.ADMIN},
        )

        instructor_user, _ = User.objects.get_or_create(
            username="test_instructor",
            defaults={
                "email": "instructor@test.com",
                "first_name": "Test",
                "last_name": "Instructor",
            },
        )
        instructor_profile, _ = UserProfile.objects.get_or_create(
            user=instructor_user,
            defaults={
                "firebase_uid": "test_instructor_uid",
                "role": UserRole.INSTRUCTOR,
            },
        )

        student_user, _ = User.objects.get_or_create(
            username="test_student",
            defaults={
                "email": "student@test.com",
                "first_name": "Test",
                "last_name": "Student",
            },
        )
        student_profile, _ = UserProfile.objects.get_or_create(
            user=student_user,
            defaults={"firebase_uid": "test_student_uid", "role": UserRole.USER},
        )

        self.stdout.write(self.style.SUCCESS("✓ Created test users"))

        # Create a test course
        course, created = Course.objects.get_or_create(
            course_id="CS101-FALL2024",
            defaults={
                "name": "Introduction to Computer Science",
                "description": "A comprehensive introduction to CS fundamentals",
                "is_active": True,
                "enrollment_open": True,
            },
        )
        CourseInstructor.objects.get_or_create(
            course=course,
            user=instructor_user,
            defaults={"role": "primary"},
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f"✓ Created course: {course.course_id}")
            )
        else:
            self.stdout.write(
                self.style.WARNING(f"! Course already exists: {course.course_id}")
            )

        # Add problem sets to the course
        problem_sets = ProblemSet.objects.filter(is_public=True)[:3]
        for i, ps in enumerate(problem_sets):
            cps, created = CourseProblemSet.objects.get_or_create(
                course=course,
                problem_set=ps,
                defaults={"order": i, "is_required": True},
            )
            if created:
                self.stdout.write(f"  Added problem set: {ps.title}")

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Course has {course.problem_sets.count()} problem sets"
            )
        )

        # Enroll student
        enrollment, created = CourseEnrollment.objects.get_or_create(
            user=student_user, course=course, defaults={"is_active": True}
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Enrolled {student_user.username} in {course.course_id}"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(f"! {student_user.username} already enrolled")
            )

        # Display course info
        self.stdout.write("\n" + self.style.SUCCESS("=== Course Information ==="))
        self.stdout.write(f"Course ID: {course.course_id}")
        self.stdout.write(f"Name: {course.name}")
        from purplex.problems_app.repositories.course_instructor_repository import (
            CourseInstructorRepository,
        )

        instructor_name = (
            CourseInstructorRepository.get_primary_instructor_names(course)
            or "Unknown Instructor"
        )
        self.stdout.write(f"Instructor: {instructor_name}")
        self.stdout.write(f"Problem Sets: {course.problem_sets.count()}")
        self.stdout.write(
            f"Enrolled Students: {course.enrollments.filter(is_active=True).count()}"
        )

        # List problem sets
        self.stdout.write("\nProblem Sets:")
        for cps in course.courseproblemset_set.order_by("order"):
            self.stdout.write(
                f"  {cps.order + 1}. {cps.problem_set.title} ({'Required' if cps.is_required else 'Optional'})"
            )

        # List enrolled students
        self.stdout.write("\nEnrolled Students:")
        for enrollment in course.enrollments.filter(is_active=True):
            self.stdout.write(
                f"  - {enrollment.user.username} (enrolled {enrollment.enrolled_at})"
            )

        self.stdout.write("\n" + self.style.SUCCESS("=== Test Complete ==="))
        self.stdout.write("You can now test the API endpoints with these users.")
        self.stdout.write(f"Course ID for testing: {course.course_id}")
