"""Course and enrollment models."""

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from .problem_set import ProblemSet


class Course(models.Model):
    """Course model for organizing problem sets into courses."""

    course_id = models.CharField(
        max_length=50,
        unique=True,
        help_text="User-defined course ID (e.g., CS101-FALL2024)",
    )
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    # CRITICAL: Changed from CASCADE to PROTECT to prevent accidental data loss
    # Deleting an instructor should not cascade-delete all their courses and student data
    instructor = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="instructed_courses"
    )
    problem_sets = models.ManyToManyField(
        ProblemSet, through="CourseProblemSet", related_name="courses"
    )
    is_active = models.BooleanField(default=True)
    enrollment_open = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)  # Soft delete
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "problems_app"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["course_id"]),
            models.Index(fields=["instructor", "is_active"]),
            models.Index(fields=["is_deleted", "is_active"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.course_id)
        super().save(*args, **kwargs)

    def soft_delete(self):
        """Soft delete the course"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.is_active = False
        self.enrollment_open = False
        self.save()

    def __str__(self):
        return f"{self.course_id} - {self.name}"


class CourseProblemSet(models.Model):
    """Through model for Course-ProblemSet relationship with ordering."""

    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    problem_set = models.ForeignKey(ProblemSet, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)
    added_at = models.DateTimeField(auto_now_add=True)
    is_required = models.BooleanField(default=True)
    # Track the version of problem set membership when added
    problem_set_version = models.IntegerField(default=1)

    class Meta:
        app_label = "problems_app"
        ordering = ["order"]
        unique_together = ["course", "problem_set"]

    def __str__(self):
        return (
            f"{self.course.course_id} - {self.problem_set.title} (Order: {self.order})"
        )


class CourseEnrollment(models.Model):
    """Track student enrollment in courses."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="course_enrollments"
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="enrollments"
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "problems_app"
        unique_together = ["user", "course"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["course", "is_active"]),
        ]

    def __str__(self):
        return f"{self.user.username} enrolled in {self.course.course_id}"
