"""
Spec problem types - problems where student writes NL, LLM generates code, code is tested.

Hierarchy:
- SpecProblem (abstract) - shared fields and methods
  - EiplProblem - student explains code
  - PromptProblem - student explains image
"""
from django.db import models
from django.core.exceptions import ValidationError
import re

from .base import Problem


class SpecProblem(Problem):
    """
    Abstract base for spec-based problems.

    Flow: Student writes natural language -> LLM generates code -> Code is tested.
    Supports optional segmentation analysis for comprehension depth.
    """

    class Meta:
        abstract = True

    # Subclasses override this to control segmentation_enabled default
    SEGMENTATION_DEFAULT_ENABLED = True

    # Code execution context
    reference_solution = models.TextField(
        help_text="Reference implementation for test validation"
    )
    function_signature = models.TextField(
        help_text="Function signature with type hints for test case parsing"
    )
    function_name = models.CharField(
        max_length=50,
        blank=True,
        help_text="Auto-extracted from reference_solution if not provided"
    )
    memory_limit = models.PositiveIntegerField(
        default=128,
        help_text="Memory limit in MB for code execution"
    )

    # LLM configuration
    llm_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="LLM settings: {model, temperature, max_tokens}"
    )

    # Segmentation configuration
    segmentation_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Segmentation settings: {enabled, min_segments, examples}"
    )
    segmentation_threshold = models.PositiveIntegerField(
        default=2,
        help_text="Max segments for high-level comprehension (fewer = better)"
    )
    requires_highlevel_comprehension = models.BooleanField(
        default=True,
        help_text="Require high-level comprehension for full credit"
    )

    @property
    def segmentation_enabled(self) -> bool:
        """Check if segmentation is enabled for this problem."""
        return (self.requires_highlevel_comprehension and
                self.segmentation_config.get('enabled', self.SEGMENTATION_DEFAULT_ENABLED))

    @property
    def get_segmentation_threshold(self):
        if self.segmentation_threshold and self.segmentation_threshold > 0:
            return self.segmentation_threshold
        return self.segmentation_config.get('threshold', 2)

    def get_segmentation_examples(self):
        return self.segmentation_config.get('examples', {})

    @property
    def test_cases_count(self):
        return self.test_cases.count()

    @property
    def visible_test_cases_count(self):
        return self.test_cases.filter(is_hidden=False).count()

    def clean(self):
        """Validate required fields for spec problems."""
        super().clean()
        if not self.reference_solution:
            raise ValidationError({
                'reference_solution': 'Required for this problem type'
            })
        if not self.function_signature:
            raise ValidationError({
                'function_signature': 'Required for this problem type'
            })
        if self.function_name and not self.function_name.isidentifier():
            raise ValidationError({
                'function_name': 'Must be a valid Python identifier'
            })

    def save(self, *args, **kwargs):
        """Auto-extract function_name from reference_solution if not provided."""
        if not self.function_name and self.reference_solution:
            match = re.match(r'def\s+(\w+)\s*\(', self.reference_solution)
            if match:
                self.function_name = match.group(1)
        super().save(*args, **kwargs)


class EiplProblem(SpecProblem):
    """
    Explain in Plain Language.

    Student explains what code does in natural language.
    LLM generates code variations from the explanation.
    Variations are tested against test cases.
    """

    SEGMENTATION_DEFAULT_ENABLED = True

    class Meta:
        app_label = 'problems_app'
        verbose_name = "EiPL Problem"
        verbose_name_plural = "EiPL Problems"

    @property
    def polymorphic_type(self) -> str:
        return 'eipl'

    def __str__(self):
        return f"[EiPL] {self.title}"


class PromptProblem(SpecProblem):
    """
    Image-based EiPL variant.

    Student sees an image instead of code, writes explanation.
    Same pipeline as EiPL otherwise.
    """

    SEGMENTATION_DEFAULT_ENABLED = False

    # Image display (Prompt-specific fields)
    image_url = models.URLField(
        help_text="URL of the problem image"
    )
    image_alt_text = models.CharField(
        max_length=500,
        blank=True,
        help_text="Alt text for accessibility"
    )

    class Meta:
        app_label = 'problems_app'
        verbose_name = "Prompt Problem"
        verbose_name_plural = "Prompt Problems"

    @property
    def polymorphic_type(self) -> str:
        return 'prompt'

    def clean(self):
        """Validate Prompt-specific fields."""
        super().clean()
        if not self.image_url:
            raise ValidationError({
                'image_url': 'Required for prompt problems'
            })

    def __str__(self):
        return f"[Prompt] {self.title}"
