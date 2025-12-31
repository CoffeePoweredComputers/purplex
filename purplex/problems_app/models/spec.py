"""
Spec problem types - problems where student writes NL, LLM generates code, code is tested.

Hierarchy:
- SpecProblem (abstract) - shared fields and methods
  - EiplProblem - student explains code
  - PromptProblem - student explains image
"""

import re

from django.core.exceptions import ValidationError
from django.db import models

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
        help_text="Auto-extracted from reference_solution if not provided",
    )
    memory_limit = models.PositiveIntegerField(
        default=128, help_text="Memory limit in MB for code execution"
    )

    # LLM configuration
    llm_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="LLM settings: {model, temperature, max_tokens}",
    )

    # Segmentation configuration
    segmentation_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Segmentation settings: {enabled, min_segments, examples}",
    )
    segmentation_threshold = models.PositiveIntegerField(
        default=2,
        help_text="Max segments for high-level comprehension (fewer = better)",
    )
    requires_highlevel_comprehension = models.BooleanField(
        default=True, help_text="Require high-level comprehension for full credit"
    )

    @property
    def segmentation_enabled(self) -> bool:
        """Check if segmentation is enabled for this problem."""
        return self.requires_highlevel_comprehension and self.segmentation_config.get(
            "enabled", self.SEGMENTATION_DEFAULT_ENABLED
        )

    @property
    def get_segmentation_threshold(self):
        """Return segmentation threshold from DB field only.

        Single source of truth: uses segmentation_threshold DB field.
        Falls back to default (2) if field is 0 or unset.
        """
        return self.segmentation_threshold if self.segmentation_threshold > 0 else 2

    def get_segmentation_examples(self):
        return self.segmentation_config.get("examples", {})

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
            raise ValidationError(
                {"reference_solution": "Required for this problem type"}
            )
        if not self.function_signature:
            raise ValidationError(
                {"function_signature": "Required for this problem type"}
            )
        if self.function_name and not self.function_name.isidentifier():
            raise ValidationError(
                {"function_name": "Must be a valid Python identifier"}
            )

    def save(self, *args, **kwargs):
        """Auto-extract function_name from reference_solution if not provided."""
        if not self.function_name and self.reference_solution:
            match = re.match(r"def\s+(\w+)\s*\(", self.reference_solution)
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
        app_label = "problems_app"
        verbose_name = "Explain in Plain Language"
        verbose_name_plural = "Explain in Plain Language Problems"

    @property
    def polymorphic_type(self) -> str:
        return "eipl"

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
    image_url = models.URLField(help_text="URL of the problem image")
    image_alt_text = models.CharField(
        max_length=500, blank=True, help_text="Alt text for accessibility"
    )

    class Meta:
        app_label = "problems_app"
        verbose_name = "Prompt Problem"
        verbose_name_plural = "Prompt Problems"

    @property
    def polymorphic_type(self) -> str:
        return "prompt"

    def clean(self):
        """Validate Prompt-specific fields."""
        super().clean()
        if not self.image_url:
            raise ValidationError({"image_url": "Required for prompt problems"})

    def __str__(self):
        return f"[Prompt] {self.title}"


class DebugFixProblem(SpecProblem):
    """
    Debug Fix problem type.

    Student receives buggy code and must fix it to pass all test cases.
    No LLM involved - student directly edits code.
    """

    SEGMENTATION_DEFAULT_ENABLED = False

    # Debug fix specific fields
    buggy_code = models.TextField(
        help_text="Code with intentional bug(s) for student to fix"
    )
    bug_hints = models.JSONField(
        default=list,
        blank=True,
        help_text="Progressive hints: [{level: 1, text: 'Check line 5'}, ...]",
    )
    allow_complete_rewrite = models.BooleanField(
        default=True, help_text="If False, require minimal diff from buggy_code"
    )

    class Meta:
        app_label = "problems_app"
        verbose_name = "Debug and Fix Code"
        verbose_name_plural = "Debug and Fix Code Problems"

    @property
    def polymorphic_type(self) -> str:
        return "debug_fix"

    def clean(self):
        """Validate Debug Fix specific fields."""
        super().clean()
        if not self.buggy_code:
            raise ValidationError({"buggy_code": "Required for debug fix problems"})

    def __str__(self):
        return f"[DebugFix] {self.title}"


class ProbeableCodeProblem(SpecProblem):
    """
    Probeable Code problem type.

    Student discovers hidden function behavior by querying an oracle (reference_solution),
    then writes code that implements the same behavior.

    Flow:
    1. Student sees function signature (optionally)
    2. Student probes oracle with inputs, gets outputs (sync API)
    3. Probe limit enforced based on probe_mode
    4. Student writes code implementing the discovered behavior
    5. Submit code (async): Tests against hidden test cases

    Probe Modes:
    - block: N probes total, then disabled permanently
    - cooldown: N probes -> submit X times -> get M more probes
    - explore: Unlimited probing
    """

    SEGMENTATION_DEFAULT_ENABLED = False

    PROBE_MODE_CHOICES = [
        ("block", "Block after limit"),
        ("cooldown", "Cooldown refill"),
        ("explore", "Unlimited"),
    ]

    # Display configuration
    show_function_signature = models.BooleanField(
        default=True, help_text="Show function parameters/types to student"
    )

    # Probe limit configuration
    probe_mode = models.CharField(
        max_length=20,
        choices=PROBE_MODE_CHOICES,
        default="explore",
        help_text="How probe limits are enforced",
    )
    max_probes = models.PositiveIntegerField(
        default=10, help_text="Initial probe budget (ignored for 'explore' mode)"
    )
    cooldown_attempts = models.PositiveIntegerField(
        default=3,
        help_text="Submission attempts required before probe refill (cooldown mode only)",
    )
    cooldown_refill = models.PositiveIntegerField(
        default=5,
        help_text="Number of probes granted after cooldown (cooldown mode only)",
    )

    class Meta:
        app_label = "problems_app"
        verbose_name = "Probeable Problem (Code)"
        verbose_name_plural = "Probeable Problems (Code)"

    @property
    def polymorphic_type(self) -> str:
        return "probeable_code"

    def clean(self):
        """Validate Probeable Code specific fields."""
        super().clean()
        if self.probe_mode == "cooldown":
            if self.cooldown_attempts < 1:
                raise ValidationError(
                    {"cooldown_attempts": "Must be at least 1 for cooldown mode"}
                )
            if self.cooldown_refill < 1:
                raise ValidationError(
                    {"cooldown_refill": "Must be at least 1 for cooldown mode"}
                )

    def __str__(self):
        return f"[ProbeableCode] {self.title}"


class ProbeableSpecProblem(SpecProblem):
    """
    Probeable Spec problem type.

    Like EiPL but student first discovers behavior via oracle probes,
    THEN writes natural language explanation that gets converted to code by LLM.

    Flow:
    1. Student sees function signature (optionally)
    2. Student probes oracle with inputs, gets outputs (sync API)
    3. Probe limit enforced based on probe_mode
    4. Student writes NL explanation of the function
    5. LLM generates code from explanation (reuses EiPL pipeline)
    6. Code tested against test cases

    Grading: Test pass + comprehension level (reuses EiPL logic)
    """

    SEGMENTATION_DEFAULT_ENABLED = True  # Uses comprehension analysis

    PROBE_MODE_CHOICES = [
        ("block", "Block after limit"),
        ("cooldown", "Cooldown refill"),
        ("explore", "Unlimited"),
    ]

    # Display configuration
    show_function_signature = models.BooleanField(
        default=True, help_text="Show function parameters/types to student"
    )

    # Probe limit configuration
    probe_mode = models.CharField(
        max_length=20,
        choices=PROBE_MODE_CHOICES,
        default="explore",
        help_text="How probe limits are enforced",
    )
    max_probes = models.PositiveIntegerField(
        default=10, help_text="Initial probe budget (ignored for 'explore' mode)"
    )
    cooldown_attempts = models.PositiveIntegerField(
        default=3,
        help_text="Submission attempts required before probe refill (cooldown mode only)",
    )
    cooldown_refill = models.PositiveIntegerField(
        default=5,
        help_text="Number of probes granted after cooldown (cooldown mode only)",
    )

    class Meta:
        app_label = "problems_app"
        verbose_name = "Probeable Problem (Explanation)"
        verbose_name_plural = "Probeable Problems (Explanation)"

    @property
    def polymorphic_type(self) -> str:
        return "probeable_spec"

    def clean(self):
        """Validate Probeable Spec specific fields."""
        super().clean()
        if self.probe_mode == "cooldown":
            if self.cooldown_attempts < 1:
                raise ValidationError(
                    {"cooldown_attempts": "Must be at least 1 for cooldown mode"}
                )
            if self.cooldown_refill < 1:
                raise ValidationError(
                    {"cooldown_refill": "Must be at least 1 for cooldown mode"}
                )

    def __str__(self):
        return f"[ProbeableSpec] {self.title}"
