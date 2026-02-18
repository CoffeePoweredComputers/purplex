"""User progress tracking models."""

from datetime import timedelta

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Avg, Count, Max, Min, Q
from django.utils import timezone

from .base import Problem
from .course import Course
from .problem_set import ProblemSet


class UserProgress(models.Model):
    """Tracks user progress on individual problems within a specific problem set and course context."""

    # CRITICAL: Use SET_NULL for user to preserve analytics data even if account deleted
    # Use PROTECT for problem/set/course to prevent deletion of content with progress data
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    problem = models.ForeignKey(Problem, on_delete=models.PROTECT)
    problem_set = models.ForeignKey(ProblemSet, on_delete=models.PROTECT, null=True)
    course = models.ForeignKey(Course, on_delete=models.PROTECT, null=True, blank=True)
    problem_version = models.PositiveIntegerField(default=1)

    # Simplified status: just completed or not completed
    status = models.CharField(
        max_length=20,
        choices=[
            ("not_started", "Not Started"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
        ],
        default="not_started",
    )

    # Grade per GRADING_PIPELINE.md specification
    grade = models.CharField(
        max_length=20,
        choices=[
            ("incomplete", "Incomplete"),
            ("partial", "Partially Complete"),
            ("complete", "Complete"),
        ],
        default="incomplete",
        help_text="Grade based on correctness and high-levelness dimensions",
        db_index=True,
    )

    # Scoring and attempts
    best_score = models.IntegerField(default=0)
    average_score = models.FloatField(default=0)
    attempts = models.IntegerField(default=0)
    successful_attempts = models.IntegerField(default=0)

    # Timing
    first_attempt = models.DateTimeField(null=True, blank=True)
    last_attempt = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    total_time_spent = models.DurationField(default=timedelta(0))

    # Learning metrics
    hints_used = models.IntegerField(default=0)
    consecutive_successes = models.IntegerField(default=0)
    days_to_complete = models.IntegerField(null=True, blank=True)

    # Cached aggregates for performance
    is_completed = models.BooleanField(default=False, db_index=True)
    completion_percentage = models.IntegerField(default=0, db_index=True)

    class Meta:
        app_label = "problems_app"
        unique_together = ["user", "problem", "problem_set", "course"]
        indexes = [
            models.Index(fields=["user", "problem_set", "is_completed"]),
            models.Index(fields=["user", "problem_set", "status"]),
            models.Index(fields=["problem", "problem_set", "status"]),
            models.Index(fields=["user", "problem_set", "-last_attempt"]),
            models.Index(fields=["user", "course", "problem_set", "is_completed"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.problem_set.title} - {self.problem.title} ({self.status})"


class UserProblemSetProgress(models.Model):
    """Cached aggregate progress for problem sets with course context."""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    problem_set = models.ForeignKey(ProblemSet, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)

    total_problems = models.IntegerField(default=0)
    completed_problems = models.IntegerField(default=0)
    in_progress_problems = models.IntegerField(default=0)
    average_score = models.FloatField(default=0)

    first_attempt = models.DateTimeField(null=True, blank=True)
    last_activity = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    completion_percentage = models.IntegerField(default=0, db_index=True)
    is_completed = models.BooleanField(default=False, db_index=True)

    class Meta:
        app_label = "problems_app"
        unique_together = ["user", "problem_set", "course"]
        indexes = [
            models.Index(fields=["user", "course", "-last_activity"]),
            models.Index(fields=["problem_set", "course", "-completion_percentage"]),
        ]

    @classmethod
    def update_from_progress(cls, user_progress):
        """
        Update problem set progress when individual problem progress changes.

        Recalculates aggregates from UserProgress (source of truth) and writes
        the rollup via update_or_create. Concurrent rollups for the same tuple
        are eventually consistent — each recalculates from source of truth, so
        the next call self-corrects any stale data.
        """
        # Recalculate aggregates from UserProgress (source of truth)
        stats = UserProgress.objects.filter(
            user=user_progress.user,
            problem_set=user_progress.problem_set,
            course=user_progress.course,
        ).aggregate(
            total=Count("id"),
            completed=Count("id", filter=Q(is_completed=True)),
            in_progress=Count("id", filter=Q(status="in_progress")),
            avg_score=Avg("best_score"),
            first_attempt=Min("first_attempt"),
            last_activity=Max("last_attempt"),
        )

        # Calculate completion metrics
        total_problems = user_progress.problem_set.problems.count()
        completed = stats["completed"] or 0
        completion_pct = int(
            (completed / total_problems * 100) if total_problems > 0 else 0
        )
        is_completed = (completed == total_problems) if total_problems > 0 else False

        # Atomic update_or_create (completed_at omitted — preserved on UPDATE, defaults to NULL on INSERT)
        set_progress, created = cls.objects.update_or_create(
            user=user_progress.user,
            problem_set=user_progress.problem_set,
            course=user_progress.course,
            defaults={
                "total_problems": total_problems,
                "completed_problems": completed,
                "in_progress_problems": stats["in_progress"] or 0,
                "average_score": stats["avg_score"] or 0,
                "first_attempt": stats["first_attempt"],
                "last_activity": stats["last_activity"],
                "completion_percentage": completion_pct,
                "is_completed": is_completed,
            },
        )

        # Set completed_at on first completion (works for both INSERT and UPDATE)
        if is_completed and not set_progress.completed_at:
            set_progress.completed_at = timezone.now()
            set_progress.save(update_fields=["completed_at"])

    def __str__(self):
        return f"{self.user.username} - {self.problem_set.title} ({self.completion_percentage}%)"


class ProgressSnapshot(models.Model):
    """Historical snapshots for tracking progress over time."""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    problem = models.ForeignKey(
        Problem, on_delete=models.CASCADE, null=True, blank=True
    )
    problem_set = models.ForeignKey(
        ProblemSet, on_delete=models.CASCADE, null=True, blank=True
    )

    snapshot_date = models.DateField(auto_now_add=True)
    completion_percentage = models.IntegerField()
    problems_completed = models.IntegerField()
    average_score = models.FloatField()
    time_spent_today = models.DurationField(default=timedelta(0))

    class Meta:
        app_label = "problems_app"
        indexes = [
            models.Index(fields=["user", "-snapshot_date"]),
            models.Index(fields=["user", "problem", "-snapshot_date"]),
        ]
        unique_together = ["user", "problem", "problem_set", "snapshot_date"]

    def __str__(self):
        target = self.problem.title if self.problem else self.problem_set.title
        return f"{self.user.username} - {target} - {self.snapshot_date}"
