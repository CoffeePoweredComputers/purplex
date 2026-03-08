"""ProblemSet and ProblemSetMembership models."""

from django.contrib.auth.models import User
from django.db import models
from django.utils.text import slugify

from .base import Problem


class ProblemSet(models.Model):
    """Collection of problems grouped for educational purposes."""

    slug = models.SlugField(max_length=100, unique=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    problems = models.ManyToManyField(
        Problem, through="ProblemSetMembership", related_name="problem_sets", blank=True
    )
    icon = models.ImageField(upload_to="problem_set_icons/", null=True, blank=True)
    is_public = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        app_label = "problems_app"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = base_slug
            counter = 1
            while (
                ProblemSet.objects.filter(slug=self.slug).exclude(pk=self.pk).exists()
            ):
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    @property
    def problems_count(self):
        return self.problems.count()

    def increment_version(self):
        """Call when problem membership changes"""
        self.version = models.F("version") + 1
        self.save(update_fields=["version"])

    def __str__(self):
        return self.title


class ProblemSetMembership(models.Model):
    """Through model for Problem-ProblemSet relationship with ordering."""

    problem_set = models.ForeignKey(ProblemSet, on_delete=models.CASCADE)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "problems_app"
        ordering = ["order"]
        unique_together = ["problem_set", "problem"]

    def __str__(self):
        return f"{self.problem_set.title} - {self.problem.title}"
