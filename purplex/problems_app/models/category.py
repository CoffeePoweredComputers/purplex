"""Problem category model."""

from django.db import models
from django.utils.text import slugify


class ProblemCategory(models.Model):
    """Category for organizing problems."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField()
    icon = models.ImageField(upload_to="category_icons/", null=True, blank=True)
    color = models.CharField(
        max_length=7, default="#6366f1", help_text="Hex color code"
    )
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "problems_app"
        ordering = ["order", "name"]
        verbose_name_plural = "Problem Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = base_slug
            counter = 1
            while (
                ProblemCategory.objects.filter(slug=self.slug)
                .exclude(pk=self.pk)
                .exists()
            ):
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
