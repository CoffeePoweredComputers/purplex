"""
Polymorphic base Problem model.

This module contains the base Problem class that all problem types inherit from.
Uses django-polymorphic to enable true polymorphic queries.
"""

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify
from polymorphic.models import PolymorphicModel

from .category import ProblemCategory

# Constants
DEFAULT_COMPLETION_THRESHOLD = 100


class Problem(PolymorphicModel):
    """
    Polymorphic base class for all problem types.

    Problem.objects.all() returns correct subtypes automatically.

    Hierarchy:
    - Problem (this class)
      - StaticProblem (abstract) - no code execution
        - McqProblem
      - EiplProblem - NL -> LLM -> code -> test
      - PromptProblem - image-based variant of EiPL
      - (Future) CodeProblem - student code -> execute
    """

    DIFFICULTY_CHOICES = [
        ("easy", "Easy"),
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
    ]

    # Identity
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    title = models.CharField(max_length=200)

    description = models.TextField(
        blank=True,
        default="",
        help_text="Problem description in markdown format",
    )

    # Classification
    difficulty = models.CharField(
        max_length=20, choices=DIFFICULTY_CHOICES, default="beginner"
    )
    categories = models.ManyToManyField(
        ProblemCategory, related_name="problems", blank=True
    )
    tags = models.JSONField(default=list, blank=True, help_text="Array of tag strings")

    # Status
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)

    # Completion configuration
    completion_threshold = models.IntegerField(
        default=DEFAULT_COMPLETION_THRESHOLD,
        help_text="Minimum score required for completion",
    )
    max_attempts = models.IntegerField(
        null=True, blank=True, help_text="Maximum attempts allowed (null = unlimited)"
    )

    # Prerequisites
    prerequisites = models.ManyToManyField(
        "self", symmetrical=False, related_name="unlocks", blank=True
    )

    class Meta:
        app_label = "problems_app"
        ordering = ["difficulty", "title"]
        indexes = [
            models.Index(fields=["is_active", "-created_at"]),
            models.Index(fields=["is_active", "difficulty"]),
            models.Index(fields=["created_by", "-created_at"]),
        ]

    @property
    def polymorphic_type(self) -> str:
        """
        Return the problem type identifier for handler lookup.
        Subclasses override this to return their type name.
        """
        raise NotImplementedError("Subclasses must define polymorphic_type")

    @property
    def problem_type(self) -> str:
        """Alias for polymorphic_type for backward compatibility."""
        return self.polymorphic_type

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = base_slug
            counter = 1
            while Problem.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def clean(self):
        if self.tags and not isinstance(self.tags, list):
            raise ValidationError("Tags must be a list of strings")

    def __str__(self):
        return f"{self.title} ({self.difficulty})"
