"""
Clean redesign of submission models.
Central source of truth for all submission data.
"""

import uuid

from django.contrib.auth.models import User
from django.db import models


class Submission(models.Model):
    """
    Unified submission model for all submission types.
    Single source of truth for student work.
    """

    # Unique identifier for external references
    submission_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)

    # Core relationships
    # CRITICAL: Use SET_NULL for user to preserve submission data for research/analytics
    # even if user account is deleted. Use PROTECT for problem/set/course to prevent
    # accidental deletion of educational content that has submissions.
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="submissions"
    )
    problem = models.ForeignKey(
        "problems_app.Problem", on_delete=models.PROTECT, related_name="submissions"
    )
    problem_set = models.ForeignKey(
        "problems_app.ProblemSet",
        on_delete=models.PROTECT,
        related_name="submissions",
    )
    course = models.ForeignKey(
        "problems_app.Course",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="submissions",
    )

    # Submission metadata
    submitted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    # NOTE: Submission types should align with PROBLEM_TYPE_CHOICES in problems_app/models.py
    # Legacy types (direct_code, function_redef) kept for historical data compatibility
    submission_type = models.CharField(
        max_length=20,
        choices=[
            # Active types (have handlers in problems_app/handlers/)
            ("eipl", "Explain in Plain Language"),
            ("mcq", "Multiple Choice Question"),
            ("prompt", "Prompt (Image-based)"),
            ("refute", "Refute (Counterexample)"),
            ("debug_fix", "Debug Fix"),
            ("probeable_code", "Probeable Code"),
            ("probeable_spec", "Probeable Spec"),
            # Legacy types (no handler, historical data only)
            ("direct_code", "Direct Code Submission"),
            ("function_redef", "Function Redefinition"),
        ],
        db_index=True,
    )

    # Submission content
    raw_input = models.TextField(
        help_text="Original user input (code or natural language)"
    )
    processed_code = models.TextField(
        help_text="Final code that was executed", blank=True
    )

    # Execution metadata
    execution_status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("processing", "Processing"),
            ("completed", "Completed"),
            ("failed", "Failed"),
            ("timeout", "Timeout"),
        ],
        default="pending",
        db_index=True,
    )
    execution_time_ms = models.IntegerField(
        null=True, blank=True, help_text="Execution time in milliseconds"
    )
    memory_used_mb = models.FloatField(
        null=True, blank=True, help_text="Peak memory usage in MB"
    )

    # Results
    score = models.IntegerField(
        default=0, db_index=True, help_text="Overall score (0-100)"
    )
    passed_all_tests = models.BooleanField(default=False, db_index=True)
    completion_status = models.CharField(
        max_length=20,
        choices=[
            ("incomplete", "Incomplete"),
            ("partial", "Partial Success"),
            ("complete", "Complete Success"),
        ],
        default="incomplete",
        db_index=True,
    )

    # New grading fields per GRADING_PIPELINE.md
    is_correct = models.BooleanField(
        default=False,
        help_text="Whether the submission passes all test cases",
        db_index=True,
    )
    comprehension_level = models.CharField(
        max_length=20,
        choices=[
            ("high-level", "High-level/Relational"),
            ("low-level", "Low-level/Multistructural"),
            ("not_evaluated", "Not Evaluated"),
        ],
        default="not_evaluated",
        help_text="Comprehension level based on segmentation analysis",
    )

    # Time tracking
    time_spent = models.DurationField(
        null=True, blank=True, help_text="Time spent on this attempt"
    )

    # Deadline tracking
    is_late = models.BooleanField(
        default=False,
        db_default=False,  # Database-level default ensures NOT NULL even if Python passes None
        db_index=True,
        help_text="True if submitted after soft deadline",
    )

    # Async processing - unique constraint prevents duplicate submissions on task retry
    celery_task_id = models.CharField(
        max_length=255, null=True, blank=True, unique=True
    )

    class Meta:
        indexes = [
            models.Index(fields=["user", "problem", "course", "-submitted_at"]),
            models.Index(fields=["user", "problem_set", "course", "-submitted_at"]),
            models.Index(fields=["course", "problem_set", "-score"]),
            models.Index(fields=["submission_type", "execution_status"]),
        ]
        ordering = ["-submitted_at"]

    def __str__(self):
        course_context = f" ({self.course.course_id})" if self.course else ""
        return f"{self.user.username} - {self.problem.title}{course_context} - {self.score}%"


class TestExecution(models.Model):
    """
    Individual test case execution results.
    Separate model for efficient querying and detailed tracking.
    """

    submission = models.ForeignKey(
        Submission, on_delete=models.CASCADE, related_name="test_executions"
    )
    test_case = models.ForeignKey("problems_app.TestCase", on_delete=models.CASCADE)

    # Link to specific code variation (for EiPL submissions with multiple variations)
    code_variation = models.ForeignKey(
        "CodeVariation",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="test_executions",
        help_text="Which code variation this test was run against (for EiPL)",
    )

    # Execution details
    execution_order = models.IntegerField(help_text="Order in which test was executed")
    passed = models.BooleanField(default=False, db_index=True)

    # Input/Output tracking
    input_values = models.JSONField(help_text="Actual input values used")
    expected_output = models.JSONField(help_text="Expected output")
    actual_output = models.JSONField(
        null=True, blank=True, help_text="What the code produced"
    )

    # Error tracking
    error_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        choices=[
            ("none", "No Error"),
            ("wrong_output", "Wrong Output"),
            ("runtime_error", "Runtime Error"),
            ("timeout", "Timeout"),
            ("memory_exceeded", "Memory Limit Exceeded"),
            ("syntax_error", "Syntax Error"),
        ],
        default="none",
    )
    error_message = models.TextField(null=True, blank=True)
    error_traceback = models.TextField(
        null=True, blank=True, help_text="Full traceback for debugging"
    )

    # Performance metrics
    execution_time_ms = models.IntegerField(null=True, blank=True)
    memory_used_kb = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ["execution_order"]
        indexes = [
            models.Index(fields=["submission", "passed"]),
            models.Index(fields=["test_case", "passed"]),
        ]

    def __str__(self):
        return f"Test {self.execution_order} for submission {self.submission.submission_id}: {'✓' if self.passed else '✗'}"


class HintActivation(models.Model):
    """
    Track which hints were activated during a submission.
    """

    submission = models.ForeignKey(
        Submission, on_delete=models.CASCADE, related_name="hint_activations"
    )
    hint = models.ForeignKey("problems_app.ProblemHint", on_delete=models.CASCADE)

    activated_at = models.DateTimeField(auto_now_add=True)
    activation_order = models.IntegerField(
        help_text="Order in which hints were activated"
    )

    # Track how the hint was triggered
    trigger_type = models.CharField(
        max_length=20,
        choices=[
            ("manual", "Manual Request"),
            ("auto_attempts", "Auto After N Attempts"),
            ("auto_time", "Auto After Time"),
            ("instructor", "Instructor Provided"),
        ],
        default="manual",
    )

    # Track effectiveness (for research)
    viewed_duration_seconds = models.IntegerField(
        null=True, blank=True, help_text="How long hint was displayed"
    )
    was_helpful = models.BooleanField(
        null=True, blank=True, help_text="User feedback on helpfulness"
    )

    class Meta:
        ordering = ["activation_order"]
        unique_together = ["submission", "hint"]

    def __str__(self):
        return f"{self.hint.hint_type} hint for {self.submission.submission_id}"


class CodeVariation(models.Model):
    """
    For EiPL submissions: track each generated code variation.
    """

    submission = models.ForeignKey(
        Submission, on_delete=models.CASCADE, related_name="code_variations"
    )

    variation_index = models.IntegerField(help_text="Index of this variation (0-based)")
    generated_code = models.TextField()

    # Track which variation was selected as best
    is_selected = models.BooleanField(
        default=False, help_text="Was this the best variation?"
    )

    # Performance of this specific variation
    tests_passed = models.IntegerField(default=0)
    tests_total = models.IntegerField(default=0)
    score = models.IntegerField(default=0)

    # Generation metadata
    model_used = models.CharField(max_length=50, default="gpt-4o-mini")
    prompt_tokens = models.IntegerField(null=True, blank=True)
    completion_tokens = models.IntegerField(null=True, blank=True)
    generation_time_ms = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ["variation_index"]
        unique_together = ["submission", "variation_index"]

    def __str__(self):
        return f"Variation {self.variation_index} for {self.submission.submission_id} - Score: {self.score}%"


class SegmentationAnalysis(models.Model):
    """
    Comprehension analysis for EiPL submissions.
    """

    submission = models.OneToOneField(
        Submission, on_delete=models.CASCADE, related_name="segmentation"
    )

    # Core analysis results
    segment_count = models.IntegerField(db_index=True)
    comprehension_level = models.CharField(
        max_length=20,
        choices=[
            ("relational", "Relational (Good)"),
            ("multi_structural", "Multi-structural (Needs Work)"),
        ],
        db_index=True,
    )

    # Detailed segment data
    segments = models.JSONField(
        help_text="List of identified segments with descriptions"
    )
    code_mappings = models.JSONField(help_text="Mapping of segments to code lines")

    # Analysis metadata
    confidence_score = models.FloatField(
        help_text="Model confidence in segmentation (0-1)"
    )
    processing_time_ms = models.IntegerField()
    model_used = models.CharField(max_length=50, default="gpt-4o-mini")

    # Educational feedback
    feedback_message = models.TextField(
        help_text="Constructive feedback for the student"
    )
    suggested_improvements = models.JSONField(
        default=list, help_text="Specific suggestions for improvement"
    )

    # Pass/fail status based on threshold
    passed = models.BooleanField(
        default=False,
        help_text="Whether segmentation meets the threshold (segment_count <= threshold)",
        db_index=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["comprehension_level", "segment_count"]),
        ]

    def __str__(self):
        return f"Segmentation for {self.submission.submission_id}: {self.segment_count} segments ({self.comprehension_level})"


class SubmissionFeedback(models.Model):
    """
    Instructor or automated feedback on submissions.
    """

    submission = models.ForeignKey(
        Submission, on_delete=models.CASCADE, related_name="feedback"
    )

    # Who provided feedback
    provided_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    is_automated = models.BooleanField(default=False)

    # Feedback content
    feedback_type = models.CharField(
        max_length=20,
        choices=[
            ("praise", "Praise"),
            ("suggestion", "Suggestion"),
            ("correction", "Correction"),
            ("hint", "Hint"),
        ],
    )
    message = models.TextField()

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    is_visible_to_student = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.feedback_type} feedback for {self.submission.submission_id}"


class ActivityEvent(models.Model):
    """
    Append-only activity event log for durable user action tracking.
    Records must not be updated or deleted after creation.

    Event types use dot-separated namespaces (e.g., probe.execute, hint.view).
    New types can be added without migration — naming convention enforced in
    ActivityEventService.

    Retention: DATA_RETENTION["ACTIVITY_EVENTS_YEARS"] (3 years).
    Estimated volume: ~6M rows/semester (500 students x 100 events/hr x 4hr x 30d).
    """

    # Core relationships — all SET_NULL to preserve events for research
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_events",
        help_text="SET_NULL preserves event for research when user deleted",
    )
    problem = models.ForeignKey(
        "problems_app.Problem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_events",
        help_text="SET_NULL preserves event when problem deleted",
    )
    course = models.ForeignKey(
        "problems_app.Course",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_events",
        help_text="SET_NULL preserves event when course deleted",
    )

    # Event metadata
    event_type = models.CharField(
        max_length=80,
        db_index=True,
        help_text="Dot-separated namespace: probe.execute, hint.view, refute.attempt, etc.",
    )
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    payload = models.JSONField(
        default=dict,
        help_text="Event-specific data. Schema varies by event_type: "
        "probe.execute: {input: str, output: str, probe_index: int}; "
        "hint.view: {hint_type: str, problem_slug: str}; "
        "refute.attempt: {counterexample: dict, result: dict}",
    )

    # Research & privacy
    anonymous_user_id = models.CharField(
        max_length=16,
        db_index=True,
        blank=True,
        default="",
        help_text="SHA-256 hash (16 chars) via AnonymizationService, set at creation. "
        "Survives user deletion for research correlation.",
    )
    schema_version = models.PositiveSmallIntegerField(
        default=1,
        help_text="Payload schema version for forward-compatible evolution",
    )

    # Deduplication
    idempotency_key = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        help_text="Optional deduplication key, prevents duplicate recording on retry",
    )

    class Meta:
        indexes = [
            models.Index(fields=["user", "-timestamp"]),
            models.Index(fields=["event_type", "-timestamp"]),
            models.Index(fields=["course", "event_type", "-timestamp"]),
        ]
        ordering = ["-timestamp"]

    def save(self, *args, **kwargs):
        """Enforce append-only: existing records cannot be modified."""
        if self.pk and not self._state.adding:
            raise ValueError("ActivityEvent records are immutable")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion of activity event records (research data)."""
        raise ValueError("ActivityEvent records cannot be deleted")

    def __str__(self):
        return f"{self.event_type} at {self.timestamp} (user={self.user_id})"
