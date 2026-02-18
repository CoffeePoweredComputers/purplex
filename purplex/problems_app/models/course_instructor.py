"""CourseInstructor through-table for multi-instructor support."""

from django.contrib.auth.models import User
from django.db import models


class CourseInstructorRole(models.TextChoices):
    PRIMARY = "primary", "Primary Instructor"
    TA = "ta", "Teaching Assistant"


class CourseInstructor(models.Model):
    """
    Through-table linking courses to instructors with role metadata.

    Supports multiple primary instructors (full control) and teaching
    assistants (read-only access to student data/analytics).
    """

    course = models.ForeignKey(
        "problems_app.Course",
        on_delete=models.CASCADE,
        related_name="course_instructors",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="course_instructor_roles",
    )
    role = models.CharField(
        max_length=10,
        choices=CourseInstructorRole.choices,
        default=CourseInstructorRole.PRIMARY,
    )
    added_at = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        app_label = "problems_app"
        unique_together = ["course", "user"]
        indexes = [
            models.Index(fields=["course", "role"]),
            models.Index(fields=["user", "role"]),
        ]

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()}) - {self.course.course_id}"
