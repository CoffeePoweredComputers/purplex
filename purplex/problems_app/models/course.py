"""Course and enrollment models."""

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from .problem_set import ProblemSet


class ActiveCourseManager(models.Manager):
    """Default manager that excludes soft-deleted courses."""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class Course(models.Model):
    """Course model for organizing problem sets into courses."""

    objects = ActiveCourseManager()
    all_objects = models.Manager()

    course_id = models.CharField(
        max_length=50,
        unique=True,
        help_text="User-defined course ID (e.g., CS101-FALL2024)",
    )
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
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
            models.Index(fields=["is_active"]),
            models.Index(fields=["is_deleted", "is_active"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.course_id)
            self.slug = base_slug
            counter = 1
            while (
                Course.all_objects.filter(slug=self.slug).exclude(pk=self.pk).exists()
            ):
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def is_instructor(self, user) -> bool:
        """Check if user has any instructor role on this course."""
        return self.course_instructors.filter(user=user).exists()

    def is_primary_instructor(self, user) -> bool:
        """Check if user is a primary instructor on this course."""
        return self.course_instructors.filter(user=user, role="primary").exists()

    def get_primary_instructors(self):
        """Return queryset of primary CourseInstructor rows."""
        return self.course_instructors.filter(role="primary").select_related("user")

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

    DEADLINE_TYPE_CHOICES = [
        ("none", "No Deadline"),
        ("soft", "Soft Deadline"),
        ("hard", "Hard Deadline"),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    problem_set = models.ForeignKey(ProblemSet, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)
    added_at = models.DateTimeField(auto_now_add=True)
    is_required = models.BooleanField(default=True)
    # Track the version of problem set membership when added
    problem_set_version = models.IntegerField(default=1)
    # Optional due date for this problem set in this course
    due_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional due date for this problem set in this course",
    )
    # Deadline enforcement type
    deadline_type = models.CharField(
        max_length=10,
        choices=DEADLINE_TYPE_CHOICES,
        default="none",
        help_text="none: no enforcement, soft: allow late with flag, hard: block after due",
    )

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
