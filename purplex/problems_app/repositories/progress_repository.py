"""
Repository for UserProgress and related model data access.
"""

from datetime import timedelta
from typing import Any

from django.contrib.auth.models import User
from django.db.models import Avg, Sum
from django.utils import timezone

from purplex.problems_app.models import (
    Course,
    Problem,
    ProblemSet,
    ProgressSnapshot,
    UserProblemSetProgress,
    UserProgress,
)

from .base_repository import BaseRepository


class ProgressRepository(BaseRepository):
    """
    Repository for all progress-related database queries.

    This repository handles all data access for user progress tracking,
    including individual problem progress, problem set progress, and snapshots.
    """

    model_class = UserProgress

    @classmethod
    def get_user_progress(
        cls,
        user: User,
        problem: Problem,
        course: Course | None = None,
        problem_set: ProblemSet | None = None,
    ) -> UserProgress | None:
        """
        Get a user's progress for a specific problem.

        Args:
            user: The user
            problem: The problem
            course: Optional course context
            problem_set: Optional problem set context

        Returns:
            UserProgress instance or None
        """
        filters = {"user": user, "problem": problem}
        if course:
            filters["course"] = course
        if problem_set:
            filters["problem_set"] = problem_set

        return UserProgress.objects.filter(**filters).first()

    @classmethod
    def get_or_create_user_progress(
        cls, user: User, problem: Problem, course: Course | None = None
    ) -> tuple:
        """
        Get or create user progress for a problem.

        Returns:
            Tuple of (UserProgress, created)
        """
        defaults = {"attempts": 0, "hints_used": 0, "status": "not_started"}

        return UserProgress.objects.get_or_create(
            user=user, problem=problem, course=course, defaults=defaults
        )

    @classmethod
    def get_user_attempts(
        cls,
        user: User,
        problem: Problem,
        course: Course | None = None,
        problem_set: ProblemSet | None = None,
    ) -> int:
        """Get the number of attempts a user has made on a problem."""
        progress = cls.get_user_progress(user, problem, course, problem_set)
        return progress.attempts if progress else 0

    @classmethod
    def get_user_all_progress(cls, user: User, course: Course | None = None) -> list:
        """Get all progress records for a user."""
        filters = {"user": user}
        if course:
            filters["course"] = course

        return list(
            UserProgress.objects.filter(**filters)
            .select_related("course")
            .order_by("-last_attempt")
        )

    @classmethod
    def get_user_completed_problems(
        cls, user: User, course: Course | None = None
    ) -> list:
        """Get all problems completed by a user."""
        filters = {"user": user, "status": "completed"}
        if course:
            filters["course"] = course

        return list(UserProgress.objects.filter(**filters))

    @classmethod
    def get_problem_set_progress(
        cls, user: User, problem_set: ProblemSet, course: Course | None = None
    ) -> UserProblemSetProgress | None:
        """Get user's progress for a problem set."""
        filters = {"user": user, "problem_set": problem_set}
        if course:
            filters["course"] = course

        return UserProblemSetProgress.objects.filter(**filters).first()

    @classmethod
    def get_or_create_problem_set_progress(
        cls, user: User, problem_set: ProblemSet, course: Course | None = None
    ) -> tuple:
        """Get or create problem set progress."""
        defaults = {"completed_problems": 0, "average_score": 0.0}

        return UserProblemSetProgress.objects.get_or_create(
            user=user, problem_set=problem_set, course=course, defaults=defaults
        )

    @classmethod
    def update_problem_set_progress(
        cls,
        user: User,
        problem_set: ProblemSet,
        updates: dict[str, Any],
        course: Course | None = None,
    ) -> bool:
        """Update problem set progress."""
        filters = {"user": user, "problem_set": problem_set}
        if course:
            filters["course"] = course

        updated = UserProblemSetProgress.objects.filter(**filters).update(**updates)
        return updated > 0

    @classmethod
    def get_user_problem_set_progresses(
        cls, user: User, course: Course | None = None
    ) -> list:
        """Get all problem set progress records for a user."""
        filters = {"user": user}
        if course:
            filters["course"] = course

        return list(
            UserProblemSetProgress.objects.filter(**filters)
            .select_related("problem_set", "course")
            .order_by("-last_updated")
        )

    @classmethod
    def get_course_progress_summary(cls, user: User, course: Course) -> dict[str, Any]:
        """
        Get a summary of user's progress in a course.

        Returns:
            Dictionary with progress statistics
        """
        progress_qs = UserProgress.objects.filter(user=user, course=course)

        return {
            "total_problems": progress_qs.count(),
            "completed": progress_qs.filter(status="completed").count(),
            "in_progress": progress_qs.filter(status="in_progress").count(),
            "not_started": progress_qs.filter(status="not_started").count(),
            "total_attempts": progress_qs.aggregate(Sum("attempts"))["attempts__sum"]
            or 0,
            "total_hints": progress_qs.aggregate(Sum("hints_used"))["hints_used__sum"]
            or 0,
            "avg_score": progress_qs.filter(score__isnull=False).aggregate(
                Avg("score")
            )["score__avg"]
            or 0.0,
        }

    @classmethod
    def get_recent_activity(cls, user: User, days: int = 7) -> list:
        """Get user's recent activity within specified days."""
        cutoff_date = timezone.now() - timedelta(days=days)
        return list(
            UserProgress.objects.filter(user=user, last_attempt__gte=cutoff_date)
            .select_related("course")
            .order_by("-last_attempt")
        )

    @classmethod
    def create_progress_snapshot(
        cls,
        user: User,
        problem: Problem | None = None,
        problem_set: ProblemSet | None = None,
        course: Course | None = None,
        snapshot_data: dict[str, Any] = None,
    ) -> ProgressSnapshot:
        """Create a progress snapshot for tracking history."""
        return ProgressSnapshot.objects.create(
            user=user,
            problem=problem,
            problem_set=problem_set,
            course=course,
            snapshot_data=snapshot_data or {},
            snapshot_date=timezone.now(),
        )

    @classmethod
    def get_progress_snapshots(
        cls,
        user: User,
        problem: Problem | None = None,
        problem_set: ProblemSet | None = None,
        course: Course | None = None,
        days_back: int = 30,
    ) -> list:
        """Get progress snapshots for a user."""
        filters = {"user": user}
        if problem:
            filters["problem"] = problem
        if problem_set:
            filters["problem_set"] = problem_set
        if course:
            filters["course"] = course

        cutoff_date = timezone.now() - timedelta(days=days_back)
        filters["snapshot_date__gte"] = cutoff_date

        return list(
            ProgressSnapshot.objects.filter(**filters).order_by("snapshot_date")
        )

    @classmethod
    def get_problem_statistics(cls, problem: Problem) -> dict[str, Any]:
        """
        Get statistics for a specific problem across all users.

        Returns:
            Dictionary with problem statistics
        """
        progress_qs = UserProgress.objects.filter(problem=problem)

        return {
            "total_attempts": progress_qs.aggregate(Sum("attempts"))["attempts__sum"]
            or 0,
            "unique_users": progress_qs.values("user").distinct().count(),
            "completion_rate": progress_qs.filter(status="completed").count()
            / max(progress_qs.count(), 1),
            "avg_attempts": progress_qs.filter(status="completed").aggregate(
                Avg("attempts")
            )["attempts__avg"]
            or 0.0,
            "avg_hints_used": progress_qs.aggregate(Avg("hints_used"))[
                "hints_used__avg"
            ]
            or 0.0,
            "avg_score": progress_qs.filter(score__isnull=False).aggregate(
                Avg("score")
            )["score__avg"]
            or 0.0,
        }

    @classmethod
    def get_user_statistics(cls, user: User) -> dict[str, Any]:
        """
        Get overall statistics for a user.

        Returns:
            Dictionary with user statistics
        """
        progress_qs = UserProgress.objects.filter(user=user)

        return {
            "problems_attempted": progress_qs.filter(attempts__gt=0).count(),
            "problems_completed": progress_qs.filter(status="completed").count(),
            "total_attempts": progress_qs.aggregate(Sum("attempts"))["attempts__sum"]
            or 0,
            "total_hints_used": progress_qs.aggregate(Sum("hints_used"))[
                "hints_used__sum"
            ]
            or 0,
            "avg_attempts_per_problem": progress_qs.filter(
                status="completed"
            ).aggregate(Avg("attempts"))["attempts__avg"]
            or 0.0,
            "avg_score": progress_qs.filter(score__isnull=False).aggregate(
                Avg("score")
            )["score__avg"]
            or 0.0,
            "courses_enrolled": Course.objects.filter(
                enrollments__user=user, enrollments__is_active=True
            ).count(),
        }

    @classmethod
    def reset_problem_progress(
        cls, user: User, problem: Problem, course: Course | None = None
    ) -> bool:
        """Reset a user's progress for a specific problem."""
        filters = {"user": user, "problem": problem}
        if course:
            filters["course"] = course

        deleted, _ = UserProgress.objects.filter(**filters).delete()
        return deleted > 0

    @classmethod
    def get_by_ids(
        cls,
        user_id: int,
        problem_id: int,
        problem_set_id: int | None = None,
        course_id: int | None = None,
    ) -> UserProgress | None:
        """
        Get user progress by IDs.

        Returns:
            UserProgress instance or None
        """
        filters = {"user_id": user_id, "problem_id": problem_id}
        if problem_set_id:
            filters["problem_set_id"] = problem_set_id
        if course_id:
            filters["course_id"] = course_id

        return UserProgress.objects.filter(**filters).first()

    @classmethod
    def filter_by_ids(
        cls,
        user_id: int,
        problem_id: int | None = None,
        problem_set_id: int | None = None,
        course_id: int | None = None,
    ):
        """
        Filter progress records by IDs.

        Returns:
            QuerySet of UserProgress (not evaluated - allows chaining)
        """
        filters = {"user_id": user_id}
        if problem_id:
            filters["problem_id"] = problem_id
        if problem_set_id:
            filters["problem_set_id"] = problem_set_id
        if course_id:
            filters["course_id"] = course_id

        return UserProgress.objects.filter(**filters)

    @classmethod
    def filter_problem_set_by_ids(
        cls,
        user_id: int,
        problem_set_id: int | None = None,
        course_id: int | None = None,
    ) -> list:
        """
        Filter problem set progress by IDs.

        Returns:
            QuerySet of UserProblemSetProgress
        """
        filters = {"user_id": user_id}
        if problem_set_id:
            filters["problem_set_id"] = problem_set_id
        if course_id:
            filters["course_id"] = course_id

        return list(UserProblemSetProgress.objects.filter(**filters))

    @classmethod
    def get_problem_set_progress_with_relations(
        cls, user_id: int, problem_set_id: int
    ) -> dict[str, Any] | None:
        """
        Get problem set progress with related data.

        Returns:
            Dictionary with progress data or None
        """
        progress = (
            UserProblemSetProgress.objects.filter(
                user_id=user_id, problem_set_id=problem_set_id
            )
            .select_related("problem_set")
            .first()
        )

        if not progress:
            return None

        return {
            "problem_set": progress.problem_set.slug,
            "total_problems": progress.total_problems,
            "completed_problems": progress.completed_problems,
            "in_progress_problems": progress.in_progress_problems,
            "completion_percentage": progress.completion_percentage,
            "is_completed": progress.is_completed,
            "average_score": progress.average_score,
            "last_activity": progress.last_activity,
        }

    @classmethod
    def get_course_progress_summary_data(cls, user_id: int) -> list[dict[str, Any]]:
        """
        Get all course progress data for user summary.

        Returns:
            List of dictionaries with course progress data
        """
        course_progresses = (
            UserProblemSetProgress.objects.filter(user_id=user_id, course__isnull=False)
            .select_related("problem_set", "course")
            .order_by("course__course_id", "problem_set__title")
        )

        result = []
        for progress in course_progresses:
            result.append(
                {
                    "course_id": progress.course.course_id,
                    "course_name": progress.course.name,
                    "problem_set_slug": progress.problem_set.slug,
                    "problem_set_title": progress.problem_set.title,
                    "completed_problems": progress.completed_problems,
                    "total_problems": progress.total_problems,
                    "completion_percentage": progress.completion_percentage,
                    "is_completed": progress.is_completed,
                    "last_activity": progress.last_activity,
                }
            )

        return result

    @classmethod
    def get_problem_set_by_ids(
        cls, user_id: int, problem_set_id: int, course_id: int | None = None
    ) -> UserProblemSetProgress | None:
        """
        Get problem set progress by IDs.

        Returns:
            UserProblemSetProgress instance or None
        """
        filters = {"user_id": user_id, "problem_set_id": problem_set_id}
        if course_id:
            filters["course_id"] = course_id

        return UserProblemSetProgress.objects.filter(**filters).first()

    @classmethod
    def get_user_course_progress(cls, user: User, course: Course) -> list:
        """
        Get all user progress records for a specific course.

        Args:
            user: The user
            course: The course

        Returns:
            QuerySet of UserProgress records
        """
        return list(
            UserProgress.objects.filter(user=user, course=course).select_related(
                "problem_set"
            )
        )

    @classmethod
    def get_user_problem_set_progress_bulk(
        cls, user: User, problem_set_ids: list[int], courses: list[Course]
    ) -> list:
        """
        Get user's progress for multiple problem sets across multiple courses.

        Args:
            user: The user
            problem_set_ids: List of problem set IDs
            courses: List of courses

        Returns:
            QuerySet of UserProblemSetProgress records
        """
        course_ids = [course.id for course in courses]
        return list(
            UserProblemSetProgress.objects.filter(
                user=user, problem_set_id__in=problem_set_ids, course_id__in=course_ids
            ).select_related("problem_set", "course")
        )

    @classmethod
    def get_user_course_progress_by_id(
        cls, user_id: int, course_id: int
    ) -> list[dict[str, Any]]:
        """
        Get user's progress for all problems in a course.

        Args:
            user_id: ID of the user
            course_id: ID of the course

        Returns:
            List of dicts with progress data
        """
        progress_records = UserProgress.objects.filter(
            user_id=user_id, course_id=course_id
        ).select_related("problem_set")

        return [
            {
                "problem_id": p.problem_id,
                "problem_set_id": p.problem_set_id,
                "problem_set_title": p.problem_set.title if p.problem_set else "",
                "total_problems": (
                    p.problem_set.problems.count() if p.problem_set else 0
                ),
                "attempts": p.attempts,
                "is_completed": p.is_completed,
                "best_score": p.best_score,
                "last_submission_at": p.last_submission_at,
            }
            for p in progress_records
        ]

    @classmethod
    def get_user_problem_set_progress_for_course(
        cls, user_id: int, problem_set_ids: list[int], course_id: int
    ) -> list[dict[str, Any]]:
        """
        Get user's progress for specific problem sets in a course.

        Args:
            user_id: ID of the user
            problem_set_ids: List of problem set IDs
            course_id: ID of the course

        Returns:
            List of dicts with problem set progress data
        """
        if not problem_set_ids:
            return []

        progress_records = UserProblemSetProgress.objects.filter(
            user_id=user_id, problem_set_id__in=problem_set_ids, course_id=course_id
        ).select_related("problem_set")

        return [
            {
                "problem_set_id": p.problem_set_id,
                "completed_problems": p.completed_problems,
                "total_problems": p.total_problems,
                "is_completed": p.is_completed,
                "completion_percentage": p.completion_percentage,
                "last_activity": p.last_activity,
            }
            for p in progress_records
        ]

    @classmethod
    def get_user_problem_set_progress_by_course(
        cls, user: User, problem_set_ids: list[int], course: Course
    ) -> list:
        """
        Get user's progress for multiple problem sets within a specific course.

        Args:
            user: The user
            problem_set_ids: List of problem set IDs
            course: The course

        Returns:
            List of UserProblemSetProgress records
        """
        return list(
            UserProblemSetProgress.objects.filter(
                user=user, problem_set_id__in=problem_set_ids, course=course
            ).select_related("problem_set")
        )

    # =========================================================================
    # EXPORT/ANALYTICS QUERIES
    # =========================================================================

    @classmethod
    def get_for_course_export(cls, course: Course, user_ids: list[int]):
        """
        Get all progress records for course export with optimized prefetch.

        Args:
            course: Course instance
            user_ids: List of enrolled user IDs

        Returns:
            QuerySet of UserProgress with related data
        """
        return (
            UserProgress.objects.filter(course=course, user_id__in=user_ids)
            .select_related("user", "problem", "problem_set")
            .prefetch_related("problem__hints")
            .order_by("user__username", "problem__slug")
        )

    @classmethod
    def get_for_research_export(
        cls, course: Course | None = None, problem_set: ProblemSet | None = None
    ):
        """
        Get progress records for research export.

        Args:
            course: Optional course filter
            problem_set: Optional problem set filter

        Returns:
            QuerySet of UserProgress with related data
        """
        queryset = UserProgress.objects.select_related(
            "user", "problem", "problem_set", "course"
        )

        if course:
            queryset = queryset.filter(course=course)
        if problem_set:
            queryset = queryset.filter(problem_set=problem_set)

        return queryset

    @classmethod
    def get_snapshots_for_research_export(
        cls, problem_set: ProblemSet | None = None, start_date=None, end_date=None
    ):
        """
        Get progress snapshots for research export.

        Args:
            problem_set: Optional problem set filter
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            QuerySet of ProgressSnapshot with related data
        """
        queryset = ProgressSnapshot.objects.select_related(
            "user", "problem", "problem_set"
        )

        if problem_set:
            queryset = queryset.filter(problem_set=problem_set)
        if start_date:
            queryset = queryset.filter(snapshot_date__gte=start_date.date())
        if end_date:
            queryset = queryset.filter(snapshot_date__lte=end_date.date())

        return queryset

    @classmethod
    def get_for_course_analytics(cls, course: Course, student_ids: list[int]):
        """
        Get progress records for course-level analytics.

        Args:
            course: Course instance
            student_ids: List of student user IDs

        Returns:
            QuerySet of UserProgress for analytics aggregation
        """
        return UserProgress.objects.filter(course=course, user_id__in=student_ids)

    @classmethod
    def get_problem_set_for_course_analytics(
        cls, course: Course, student_ids: list[int]
    ):
        """
        Get problem set progress for course-level analytics.

        Args:
            course: Course instance
            student_ids: List of student user IDs

        Returns:
            QuerySet of UserProblemSetProgress with annotations
        """
        from django.db.models import Avg, Count, Q

        return (
            UserProblemSetProgress.objects.filter(
                course=course, user_id__in=student_ids
            )
            .values("problem_set__slug", "problem_set__title", "problem_set_id")
            .annotate(
                avg_completion=Avg("completion_percentage"),
                students_completed=Count("id", filter=Q(is_completed=True)),
                students_started=Count("id"),
            )
        )

    @classmethod
    def get_for_student_detail(cls, course: Course, user: User):
        """
        Get progress records for single student detail view.

        Args:
            course: Course instance
            user: User instance

        Returns:
            QuerySet of UserProgress with problem_set related
        """
        return UserProgress.objects.filter(course=course, user=user).select_related(
            "problem_set", "problem"
        )

    @classmethod
    def get_problem_set_for_student(cls, course: Course, user: User):
        """
        Get problem set progress for single student.

        Args:
            course: Course instance
            user: User instance

        Returns:
            QuerySet of UserProblemSetProgress
        """
        return UserProblemSetProgress.objects.filter(
            course=course, user=user
        ).select_related("problem_set")

    @classmethod
    def get_snapshots_for_student(cls, user: User, problem_sets, limit: int = 30):
        """
        Get progress snapshots for student learning trajectory.

        Args:
            user: User instance
            problem_sets: QuerySet or list of problem sets
            limit: Maximum snapshots to return

        Returns:
            QuerySet of ProgressSnapshot ordered by date
        """
        return ProgressSnapshot.objects.filter(
            user=user, problem_set__in=problem_sets
        ).order_by("snapshot_date")[:limit]

    @classmethod
    def get_for_problem_analytics(
        cls, course: Course, problem: Problem, student_ids: list[int]
    ):
        """
        Get progress records for problem-level analytics.

        Args:
            course: Course instance
            problem: Problem instance
            student_ids: List of student user IDs

        Returns:
            QuerySet of UserProgress for problem analytics
        """
        return UserProgress.objects.filter(
            course=course, problem=problem, user_id__in=student_ids
        )

    # =========================================================================
    # ATOMIC OPERATIONS WITH LOCKING
    # =========================================================================

    @classmethod
    def get_with_lock(
        cls,
        user: User,
        problem: Problem,
        problem_set: ProblemSet | None,
        course: Course | None,
        nowait: bool = True,
    ):
        """
        Get progress record with row-level lock for atomic updates.

        Args:
            user: User instance
            problem: Problem instance
            problem_set: Optional problem set
            course: Optional course
            nowait: If True, fail immediately if lock unavailable

        Returns:
            Locked UserProgress instance or None
        """
        return (
            UserProgress.objects.select_for_update(nowait=nowait)
            .filter(
                user=user,
                problem=problem,
                problem_set=problem_set,
                course=course,
            )
            .first()
        )

    @classmethod
    def create_progress_record(
        cls,
        user: User,
        problem: Problem,
        problem_set: ProblemSet | None,
        course: Course | None,
        problem_version: int,
    ) -> UserProgress:
        """
        Create a new progress record.

        Args:
            user: User instance
            problem: Problem instance
            problem_set: Optional problem set
            course: Optional course
            problem_version: Version of the problem

        Returns:
            Created UserProgress instance
        """
        return UserProgress.objects.create(
            user=user,
            problem=problem,
            problem_set=problem_set,
            course=course,
            problem_version=problem_version,
        )

    @classmethod
    def get_with_lock_by_pk(
        cls,
        user: User,
        problem: Problem,
        problem_set: ProblemSet | None,
        course: Course | None,
        nowait: bool = True,
    ):
        """
        Get progress record with lock, raising DoesNotExist if not found.

        Used after IntegrityError to get newly created record.

        Args:
            user: User instance
            problem: Problem instance
            problem_set: Optional problem set
            course: Optional course
            nowait: If True, fail immediately if lock unavailable

        Returns:
            Locked UserProgress instance

        Raises:
            UserProgress.DoesNotExist if not found
        """
        return UserProgress.objects.select_for_update(nowait=nowait).get(
            user=user,
            problem=problem,
            problem_set=problem_set,
            course=course,
        )

    @classmethod
    def get_legacy_progress(cls, user: User, problem: Problem, course: Course | None):
        """
        Get legacy progress record without problem_set for migration.

        Args:
            user: User instance
            problem: Problem instance
            course: Optional course

        Returns:
            UserProgress instance or raises DoesNotExist/MultipleObjectsReturned
        """
        return UserProgress.objects.get(
            user=user,
            problem=problem,
            problem_set__isnull=True,
            course=course if course else None,
        )

    @classmethod
    def update_or_create_snapshot(
        cls,
        user: User,
        problem: Problem,
        problem_set: ProblemSet | None,
        snapshot_date,
        defaults: dict[str, Any],
    ) -> tuple:
        """
        Update or create a progress snapshot.

        Unique constraint: (user, problem, problem_set, snapshot_date)

        Args:
            user: User instance
            problem: Problem instance
            problem_set: Optional problem set
            snapshot_date: Date for the snapshot
            defaults: Fields to set/update

        Returns:
            Tuple of (ProgressSnapshot, created)
        """
        return ProgressSnapshot.objects.update_or_create(
            user=user,
            problem=problem,
            problem_set=problem_set,
            snapshot_date=snapshot_date,
            defaults=defaults,
        )

    @classmethod
    def get_snapshots_base_queryset(cls):
        """
        Get base queryset for progress snapshots with related data.

        Used for research views that need dynamic filtering.

        Returns:
            QuerySet of ProgressSnapshot with related data
        """
        return ProgressSnapshot.objects.select_related(
            "user", "problem", "problem_set"
        ).order_by("snapshot_date", "user", "problem")
