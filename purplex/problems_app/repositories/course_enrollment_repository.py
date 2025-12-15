"""
Repository for CourseEnrollment model data access.
"""

from datetime import timedelta
from typing import Any, Dict, List, Optional

from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from purplex.problems_app.models import Course, CourseEnrollment

from .base_repository import BaseRepository


class CourseEnrollmentRepository(BaseRepository):
    """
    Repository for all CourseEnrollment-related database queries.

    This repository handles all data access for student course enrollments,
    including enrollment management and analytics.
    """

    model_class = CourseEnrollment

    @classmethod
    def get_enrollment(cls, user: User, course: Course) -> Optional[CourseEnrollment]:
        """Get a specific enrollment record for a user and course."""
        return CourseEnrollment.objects.filter(user=user, course=course).first()

    @classmethod
    def get_active_enrollment(
        cls, user: User, course: Course
    ) -> Optional[CourseEnrollment]:
        """Get an active enrollment record for a user and course."""
        return CourseEnrollment.objects.filter(
            user=user, course=course, is_active=True
        ).first()

    @classmethod
    def is_user_enrolled(cls, user: User, course: Course) -> bool:
        """Check if a user is actively enrolled in a course."""
        return CourseEnrollment.objects.filter(
            user=user, course=course, is_active=True
        ).exists()

    @classmethod
    def get_user_enrollments(
        cls, user: User, active_only: bool = True
    ) -> List[CourseEnrollment]:
        """Get all enrollments for a user."""
        queryset = CourseEnrollment.objects.filter(user=user)

        if active_only:
            queryset = queryset.filter(is_active=True)

        return list(queryset.select_related("course").order_by("-enrolled_at"))

    @classmethod
    def get_course_enrollments(
        cls, course: Course, active_only: bool = True
    ) -> List[CourseEnrollment]:
        """Get all enrollments for a course."""
        queryset = CourseEnrollment.objects.filter(course=course)

        if active_only:
            queryset = queryset.filter(is_active=True)

        return list(queryset.select_related("user").order_by("-enrolled_at"))

    @classmethod
    def get_enrollment_count(cls, course: Course, active_only: bool = True) -> int:
        """Get the count of enrollments for a course."""
        filters = {"course": course}
        if active_only:
            filters["is_active"] = True

        return CourseEnrollment.objects.filter(**filters).count()

    @classmethod
    def create_enrollment(cls, user: User, course: Course) -> CourseEnrollment:
        """Create a new enrollment for a user in a course."""
        enrollment, created = CourseEnrollment.objects.get_or_create(
            user=user, course=course, defaults={"is_active": True}
        )

        if not created and not enrollment.is_active:
            # Reactivate existing inactive enrollment
            enrollment.is_active = True
            enrollment.enrolled_at = timezone.now()
            enrollment.save()

        return enrollment

    @classmethod
    def deactivate_enrollment(cls, user: User, course: Course) -> bool:
        """Deactivate a user's enrollment in a course."""
        updated = CourseEnrollment.objects.filter(
            user=user, course=course, is_active=True
        ).update(is_active=False)

        return updated > 0

    @classmethod
    def reactivate_enrollment(cls, user: User, course: Course) -> bool:
        """Reactivate a user's enrollment in a course."""
        updated = CourseEnrollment.objects.filter(
            user=user, course=course, is_active=False
        ).update(is_active=True, enrolled_at=timezone.now())

        return updated > 0

    @classmethod
    def bulk_enroll_users(
        cls, users: List[User], course: Course
    ) -> List[CourseEnrollment]:
        """Bulk enroll multiple users in a course."""
        enrollments = []

        for user in users:
            enrollment = cls.create_enrollment(user, course)
            enrollments.append(enrollment)

        return enrollments

    @classmethod
    def bulk_deactivate_enrollments(cls, course: Course, user_ids: List[int]) -> int:
        """Bulk deactivate enrollments for specific users in a course."""
        updated = CourseEnrollment.objects.filter(
            course=course, user__id__in=user_ids, is_active=True
        ).update(is_active=False)

        return updated

    @classmethod
    def get_recent_enrollments(
        cls, course: Course, days: int = 30
    ) -> List[CourseEnrollment]:
        """Get recent enrollments for a course within specified days."""
        since_date = timezone.now() - timedelta(days=days)

        return list(
            CourseEnrollment.objects.filter(
                course=course, enrolled_at__gte=since_date, is_active=True
            )
            .select_related("user")
            .order_by("-enrolled_at")
        )

    @classmethod
    def get_enrollment_statistics(cls, course: Course) -> Dict[str, Any]:
        """Get enrollment statistics for a course."""
        enrollments = CourseEnrollment.objects.filter(course=course)

        stats = enrollments.aggregate(
            total_enrollments=Count("id"),
            active_enrollments=Count("id", filter=Q(is_active=True)),
            inactive_enrollments=Count("id", filter=Q(is_active=False)),
        )

        # Calculate enrollment trends
        now = timezone.now()
        recent_enrollments = enrollments.filter(
            enrolled_at__gte=now - timedelta(days=7), is_active=True
        ).count()

        monthly_enrollments = enrollments.filter(
            enrolled_at__gte=now - timedelta(days=30), is_active=True
        ).count()

        stats.update(
            {
                "enrollments_this_week": recent_enrollments,
                "enrollments_this_month": monthly_enrollments,
                "enrollment_rate": (
                    (stats["active_enrollments"] / stats["total_enrollments"] * 100)
                    if stats["total_enrollments"] > 0
                    else 0
                ),
            }
        )

        return stats

    @classmethod
    def get_instructor_enrollment_overview(cls, instructor: User) -> Dict[str, Any]:
        """Get enrollment overview for all courses taught by an instructor."""
        instructor_courses = Course.objects.filter(
            instructor=instructor, is_active=True
        )

        overview = {
            "total_courses": instructor_courses.count(),
            "total_students": 0,
            "course_enrollment_details": [],
        }

        for course in instructor_courses:
            enrollment_count = cls.get_enrollment_count(course)
            overview["total_students"] += enrollment_count

            overview["course_enrollment_details"].append(
                {
                    "course_id": course.course_id,
                    "course_name": course.name,
                    "enrollment_count": enrollment_count,
                    "course_slug": course.slug,
                }
            )

        return overview

    @classmethod
    def get_student_coursemates(
        cls, user: User, course: Course
    ) -> List[CourseEnrollment]:
        """Get other students enrolled in the same course."""
        return list(
            CourseEnrollment.objects.filter(course=course, is_active=True)
            .exclude(user=user)
            .select_related("user")
            .order_by("user__username")
        )

    @classmethod
    def get_common_courses(cls, user1: User, user2: User) -> List[CourseEnrollment]:
        """Get courses where both users are enrolled."""
        user1_courses = CourseEnrollment.objects.filter(
            user=user1, is_active=True
        ).values_list("course_id", flat=True)

        return list(
            CourseEnrollment.objects.filter(
                user=user2, is_active=True, course_id__in=user1_courses
            ).select_related("course")
        )

    @classmethod
    def search_enrolled_students(
        cls, course: Course, query: str
    ) -> List[CourseEnrollment]:
        """Search for enrolled students by username, first name, or last name."""
        return list(
            CourseEnrollment.objects.filter(course=course, is_active=True)
            .filter(
                Q(user__username__icontains=query)
                | Q(user__first_name__icontains=query)
                | Q(user__last_name__icontains=query)
                | Q(user__email__icontains=query)
            )
            .select_related("user")
            .order_by("user__username")
        )

    @classmethod
    def get_enrollment_timeline(
        cls, course: Course, days: int = 90
    ) -> List[Dict[str, Any]]:
        """Get enrollment timeline data for a course."""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        # Get daily enrollment counts
        enrollments = (
            CourseEnrollment.objects.filter(
                course=course,
                enrolled_at__date__gte=start_date,
                enrolled_at__date__lte=end_date,
            )
            .annotate(enrollment_date=TruncDate("enrolled_at"))
            .values("enrollment_date")
            .annotate(count=Count("id"))
            .order_by("enrollment_date")
        )

        timeline = []
        for enrollment in enrollments:
            timeline.append(
                {
                    "date": enrollment["enrollment_date"].isoformat(),
                    "enrollments": enrollment["count"],
                }
            )

        return timeline

    @classmethod
    def get_dropout_analysis(cls, course: Course) -> Dict[str, Any]:
        """Analyze dropout patterns for a course."""
        total_enrollments = CourseEnrollment.objects.filter(course=course).count()
        active_enrollments = CourseEnrollment.objects.filter(
            course=course, is_active=True
        ).count()
        dropout_count = total_enrollments - active_enrollments

        dropout_rate = (
            (dropout_count / total_enrollments * 100) if total_enrollments > 0 else 0
        )

        # Get average days before dropout (for inactive enrollments)
        inactive_enrollments = CourseEnrollment.objects.filter(
            course=course, is_active=False
        )

        avg_days_before_dropout = None
        if inactive_enrollments.exists():
            total_days = 0
            count = 0

            for enrollment in inactive_enrollments:
                # Estimate dropout date as some time after enrollment
                # This is simplified - in a real system, you might track actual dropout dates
                days_enrolled = 30  # Placeholder - would need actual dropout tracking
                total_days += days_enrolled
                count += 1

            avg_days_before_dropout = total_days / count if count > 0 else None

        return {
            "total_enrollments": total_enrollments,
            "active_enrollments": active_enrollments,
            "dropout_count": dropout_count,
            "dropout_rate": dropout_rate,
            "avg_days_before_dropout": avg_days_before_dropout,
        }

    @classmethod
    def get_capacity_info(
        cls, course: Course, max_capacity: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get capacity information for a course."""
        current_enrollment = cls.get_enrollment_count(course)

        capacity_info = {
            "current_enrollment": current_enrollment,
            "max_capacity": max_capacity,
            "spots_remaining": None,
            "is_full": False,
            "utilization_rate": None,
        }

        if max_capacity is not None:
            capacity_info["spots_remaining"] = max(0, max_capacity - current_enrollment)
            capacity_info["is_full"] = current_enrollment >= max_capacity
            capacity_info["utilization_rate"] = current_enrollment / max_capacity * 100

        return capacity_info

    @classmethod
    def cleanup_old_inactive_enrollments(cls, days_inactive: int = 365) -> int:
        """Clean up old inactive enrollment records."""
        cutoff_date = timezone.now() - timedelta(days=days_inactive)

        deleted, _ = CourseEnrollment.objects.filter(
            is_active=False, enrolled_at__lt=cutoff_date
        ).delete()

        return deleted

    @classmethod
    def get_for_course_with_users(cls, course: Course, include_inactive: bool = False):
        """
        Get enrollments for a course with user data prefetched.

        Used by export and analytics services.

        Args:
            course: Course instance
            include_inactive: Whether to include inactive enrollments

        Returns:
            QuerySet of CourseEnrollment with select_related user
        """
        queryset = CourseEnrollment.objects.filter(course=course).select_related("user")

        if not include_inactive:
            queryset = queryset.filter(is_active=True)

        return queryset

    @classmethod
    def get_active_student_ids(cls, course: Course) -> List[int]:
        """
        Get list of active student user IDs for a course.

        Args:
            course: Course instance

        Returns:
            List of user IDs
        """
        return list(
            CourseEnrollment.objects.filter(course=course, is_active=True).values_list(
                "user_id", flat=True
            )
        )

    @classmethod
    def get_enrollments_with_progress_stats(cls, course: Course):
        """
        Get enrollments with aggregated progress statistics.

        Used for instructor analytics student list view.

        Args:
            course: Course instance

        Returns:
            QuerySet of CourseEnrollment with user and progress annotations
        """
        from django.db.models import Avg, Count, Max, Q, Sum

        return (
            CourseEnrollment.objects.filter(course=course, is_active=True)
            .select_related("user")
            .annotate(
                # Aggregate progress stats for each student
                total_problems=Count(
                    "user__userprogress_set",
                    filter=Q(user__userprogress_set__course=course),
                ),
                completed_problems=Count(
                    "user__userprogress_set",
                    filter=Q(
                        user__userprogress_set__course=course,
                        user__userprogress_set__is_completed=True,
                    ),
                ),
                avg_score=Avg(
                    "user__userprogress_set__best_score",
                    filter=Q(user__userprogress_set__course=course),
                ),
                total_attempts=Sum(
                    "user__userprogress_set__attempts",
                    filter=Q(user__userprogress_set__course=course),
                ),
                total_time_spent=Sum(
                    "user__userprogress_set__total_time_spent",
                    filter=Q(user__userprogress_set__course=course),
                ),
                last_activity=Max(
                    "user__userprogress_set__last_attempt",
                    filter=Q(user__userprogress_set__course=course),
                ),
                # Problem set progress average
                avg_completion=Avg(
                    "user__userproblemsetprogress_set__completion_percentage",
                    filter=Q(user__userproblemsetprogress_set__course=course),
                ),
            )
        )
