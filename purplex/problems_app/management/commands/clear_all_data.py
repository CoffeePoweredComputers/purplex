"""
Django management command to clear ALL data from ALL tables.
This is a more comprehensive version that clears everything including users, problems, courses, etc.
Use with extreme caution!
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from purplex.problems_app.models import (
    Course,
    CourseEnrollment,
    CourseProblemSet,
    Problem,
    ProblemCategory,
    ProblemHint,
    ProblemSet,
    ProblemSetMembership,
    ProgressSnapshot,
    TestCase,
    UserProblemSetProgress,
    UserProgress,
)
from purplex.submissions.models import (
    CodeVariation,
    HintActivation,
    SegmentationAnalysis,
    Submission,
    SubmissionFeedback,
    TestExecution,
)
from purplex.users_app.models import UserProfile


class Command(BaseCommand):
    help = "Clear ALL data from ALL tables - use with extreme caution!"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting anything",
        )
        parser.add_argument(
            "--no-input",
            action="store_true",
            help="Skip confirmation prompts (for automation)",
        )
        parser.add_argument(
            "--preserve-superuser", action="store_true", help="Keep superuser accounts"
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        no_input = options["no_input"]
        preserve_superuser = options["preserve_superuser"]

        self.stdout.write(
            self.style.WARNING("🔥 DATABASE RESET TOOL - THIS WILL DELETE ALL DATA! 🔥")
        )

        if dry_run:
            self.stdout.write(
                self.style.NOTICE("Running in DRY-RUN mode - no data will be deleted")
            )

        # Get counts before deletion
        counts = self._get_data_counts()

        # Display what will be affected
        self._display_summary(counts, preserve_superuser)

        if not dry_run and not no_input:
            self.stdout.write(
                self.style.ERROR(
                    "\n⚠️  WARNING: This will DELETE ALL DATA from the database!"
                )
            )
            confirm = input('Are you ABSOLUTELY SURE? Type "DELETE ALL" to confirm: ')
            if confirm != "DELETE ALL":
                self.stdout.write(self.style.ERROR("Operation cancelled."))
                return

        # Perform the deletion
        try:
            with transaction.atomic():
                deleted_counts = self._clear_all_data(dry_run, preserve_superuser)

                if dry_run:
                    self.stdout.write(
                        self.style.SUCCESS(
                            "\n✅ DRY-RUN completed. No data was actually deleted."
                        )
                    )
                    # Rollback transaction in dry-run mode
                    transaction.set_rollback(True)
                else:
                    self._display_results(deleted_counts)
                    self.stdout.write(
                        self.style.SUCCESS("\n✅ Database cleared successfully!")
                    )

        except Exception as e:
            raise CommandError(f"Error clearing database: {e}") from e

    def _get_data_counts(self):
        """Get counts of all data that will be affected"""
        return {
            # Submission related
            "submissions": Submission.objects.count(),
            "test_executions": TestExecution.objects.count(),
            "hint_activations": HintActivation.objects.count(),
            "code_variations": CodeVariation.objects.count(),
            "segmentation_analyses": SegmentationAnalysis.objects.count(),
            "submission_feedback": SubmissionFeedback.objects.count(),
            # Progress related
            "user_progress": UserProgress.objects.count(),
            "problem_set_progress": UserProblemSetProgress.objects.count(),
            "progress_snapshots": ProgressSnapshot.objects.count(),
            # Course related
            "course_problem_sets": CourseProblemSet.objects.count(),
            "course_enrollments": CourseEnrollment.objects.count(),
            "courses": Course.objects.count(),
            # Problem related
            "problem_hints": ProblemHint.objects.count(),
            "test_cases": TestCase.objects.count(),
            "problem_set_memberships": ProblemSetMembership.objects.count(),
            "problem_sets": ProblemSet.objects.count(),
            "problem_categories": ProblemCategory.objects.count(),
            "problems": Problem.objects.count(),
            # User related
            "user_profiles": UserProfile.objects.count(),
            "users": User.objects.count(),
            "superusers": User.objects.filter(is_superuser=True).count(),
        }

    def _display_summary(self, counts, preserve_superuser):
        """Display what will be affected"""
        self.stdout.write("\n📊 Data that will be DELETED:")

        self.stdout.write("\n🔸 Submission Data:")
        self.stdout.write(f'  • Submissions: {counts["submissions"]}')
        self.stdout.write(f'  • Test Executions: {counts["test_executions"]}')
        self.stdout.write(f'  • Hint Activations: {counts["hint_activations"]}')
        self.stdout.write(f'  • Code Variations: {counts["code_variations"]}')
        self.stdout.write(
            f'  • Segmentation Analyses: {counts["segmentation_analyses"]}'
        )
        self.stdout.write(f'  • Submission Feedback: {counts["submission_feedback"]}')

        self.stdout.write("\n🔸 Progress Data:")
        self.stdout.write(f'  • User Progress Records: {counts["user_progress"]}')
        self.stdout.write(f'  • Problem Set Progress: {counts["problem_set_progress"]}')
        self.stdout.write(f'  • Progress Snapshots: {counts["progress_snapshots"]}')

        self.stdout.write("\n🔸 Course Data:")
        self.stdout.write(f'  • Course Problem Sets: {counts["course_problem_sets"]}')
        self.stdout.write(f'  • Course Enrollments: {counts["course_enrollments"]}')
        self.stdout.write(f'  • Courses: {counts["courses"]}')

        self.stdout.write("\n🔸 Problem Data:")
        self.stdout.write(f'  • Problem Hints: {counts["problem_hints"]}')
        self.stdout.write(f'  • Test Cases: {counts["test_cases"]}')
        self.stdout.write(
            f'  • Problem Set Memberships: {counts["problem_set_memberships"]}'
        )
        self.stdout.write(f'  • Problem Sets: {counts["problem_sets"]}')
        self.stdout.write(f'  • Problem Categories: {counts["problem_categories"]}')
        self.stdout.write(f'  • Problems: {counts["problems"]}')

        self.stdout.write("\n🔸 User Data:")
        self.stdout.write(f'  • User Profiles: {counts["user_profiles"]}')
        if preserve_superuser:
            regular_users = counts["users"] - counts["superusers"]
            self.stdout.write(f"  • Regular Users: {regular_users}")
            self.stdout.write(f'  • Superusers (PRESERVED): {counts["superusers"]}')
        else:
            self.stdout.write(
                f'  • All Users: {counts["users"]} (including {counts["superusers"]} superusers)'
            )

    def _clear_all_data(self, dry_run, preserve_superuser):
        """Clear all data in the correct dependency order"""
        deleted_counts = {}

        self.stdout.write("\n🗑️  Deleting data in dependency order...\n")

        # 1. Submission related (leaf nodes first)
        self.stdout.write(self.style.NOTICE("📝 Clearing submission data..."))

        if dry_run:
            count = SubmissionFeedback.objects.count()
        else:
            count, _ = SubmissionFeedback.objects.all().delete()
        deleted_counts["submission_feedback"] = count
        self.stdout.write(f"  • Submission Feedback: {count}")

        if dry_run:
            count = HintActivation.objects.count()
        else:
            count, _ = HintActivation.objects.all().delete()
        deleted_counts["hint_activations"] = count
        self.stdout.write(f"  • Hint Activations: {count}")

        if dry_run:
            count = TestExecution.objects.count()
        else:
            count, _ = TestExecution.objects.all().delete()
        deleted_counts["test_executions"] = count
        self.stdout.write(f"  • Test Executions: {count}")

        if dry_run:
            count = CodeVariation.objects.count()
        else:
            count, _ = CodeVariation.objects.all().delete()
        deleted_counts["code_variations"] = count
        self.stdout.write(f"  • Code Variations: {count}")

        if dry_run:
            count = SegmentationAnalysis.objects.count()
        else:
            count, _ = SegmentationAnalysis.objects.all().delete()
        deleted_counts["segmentation_analyses"] = count
        self.stdout.write(f"  • Segmentation Analyses: {count}")

        if dry_run:
            count = Submission.objects.count()
        else:
            count, _ = Submission.objects.all().delete()
        deleted_counts["submissions"] = count
        self.stdout.write(f"  • Submissions: {count}")

        # 2. Progress data
        self.stdout.write(self.style.NOTICE("\n📊 Clearing progress data..."))

        if dry_run:
            count = ProgressSnapshot.objects.count()
        else:
            count, _ = ProgressSnapshot.objects.all().delete()
        deleted_counts["progress_snapshots"] = count
        self.stdout.write(f"  • Progress Snapshots: {count}")

        if dry_run:
            count = UserProblemSetProgress.objects.count()
        else:
            count, _ = UserProblemSetProgress.objects.all().delete()
        deleted_counts["problem_set_progress"] = count
        self.stdout.write(f"  • Problem Set Progress: {count}")

        if dry_run:
            count = UserProgress.objects.count()
        else:
            count, _ = UserProgress.objects.all().delete()
        deleted_counts["user_progress"] = count
        self.stdout.write(f"  • User Progress: {count}")

        # 3. Course data
        self.stdout.write(self.style.NOTICE("\n🎓 Clearing course data..."))

        if dry_run:
            count = CourseProblemSet.objects.count()
        else:
            count, _ = CourseProblemSet.objects.all().delete()
        deleted_counts["course_problem_sets"] = count
        self.stdout.write(f"  • Course Problem Sets: {count}")

        if dry_run:
            count = CourseEnrollment.objects.count()
        else:
            count, _ = CourseEnrollment.objects.all().delete()
        deleted_counts["course_enrollments"] = count
        self.stdout.write(f"  • Course Enrollments: {count}")

        if dry_run:
            count = Course.objects.count()
        else:
            count, _ = Course.objects.all().delete()
        deleted_counts["courses"] = count
        self.stdout.write(f"  • Courses: {count}")

        # 4. Problem data
        self.stdout.write(self.style.NOTICE("\n🧩 Clearing problem data..."))

        if dry_run:
            count = ProblemHint.objects.count()
        else:
            count, _ = ProblemHint.objects.all().delete()
        deleted_counts["problem_hints"] = count
        self.stdout.write(f"  • Problem Hints: {count}")

        if dry_run:
            count = TestCase.objects.count()
        else:
            count, _ = TestCase.objects.all().delete()
        deleted_counts["test_cases"] = count
        self.stdout.write(f"  • Test Cases: {count}")

        if dry_run:
            count = ProblemSetMembership.objects.count()
        else:
            count, _ = ProblemSetMembership.objects.all().delete()
        deleted_counts["problem_set_memberships"] = count
        self.stdout.write(f"  • Problem Set Memberships: {count}")

        if dry_run:
            count = ProblemSet.objects.count()
        else:
            count, _ = ProblemSet.objects.all().delete()
        deleted_counts["problem_sets"] = count
        self.stdout.write(f"  • Problem Sets: {count}")

        if dry_run:
            count = ProblemCategory.objects.count()
        else:
            count, _ = ProblemCategory.objects.all().delete()
        deleted_counts["problem_categories"] = count
        self.stdout.write(f"  • Problem Categories: {count}")

        if dry_run:
            count = Problem.objects.count()
        else:
            count, _ = Problem.objects.all().delete()
        deleted_counts["problems"] = count
        self.stdout.write(f"  • Problems: {count}")

        # 5. User data
        self.stdout.write(self.style.NOTICE("\n👤 Clearing user data..."))

        if dry_run:
            count = UserProfile.objects.count()
        else:
            count, _ = UserProfile.objects.all().delete()
        deleted_counts["user_profiles"] = count
        self.stdout.write(f"  • User Profiles: {count}")

        if preserve_superuser:
            if dry_run:
                count = User.objects.filter(is_superuser=False).count()
            else:
                count, _ = User.objects.filter(is_superuser=False).delete()
            deleted_counts["regular_users"] = count
            self.stdout.write(f"  • Regular Users: {count}")
            self.stdout.write("  • Superusers: PRESERVED")
        else:
            if dry_run:
                count = User.objects.count()
            else:
                count, _ = User.objects.all().delete()
            deleted_counts["users"] = count
            self.stdout.write(f"  • All Users: {count}")

        return deleted_counts

    def _display_results(self, deleted_counts):
        """Display final results"""
        total_deleted = sum(deleted_counts.values())
        self.stdout.write(f"\n📈 Total: {total_deleted} records deleted")
        self.stdout.write(
            f'⏰ Completed at: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}'
        )
        self.stdout.write(
            '\n💡 Tip: Run "python manage.py migrate" to ensure schema is intact'
        )
        self.stdout.write(
            '💡 Tip: Run "python manage.py createsuperuser" to create a new admin user'
        )
