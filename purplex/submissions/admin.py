"""
Admin interface for the new submission system.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    ActivityEvent,
    CodeVariation,
    HintActivation,
    SegmentationAnalysis,
    Submission,
    SubmissionFeedback,
    TestExecution,
)


class TestExecutionInline(admin.TabularInline):
    """Inline view of test executions for a submission."""

    model = TestExecution
    extra = 0
    fields = ("test_case", "passed", "error_type", "execution_time_ms")
    readonly_fields = ("test_case", "passed", "error_type", "execution_time_ms")


class HintActivationInline(admin.TabularInline):
    """Inline view of hint activations for a submission."""

    model = HintActivation
    extra = 0
    fields = ("hint", "trigger_type", "activated_at", "viewed_duration_seconds")
    readonly_fields = ("hint", "trigger_type", "activated_at")


class CodeVariationInline(admin.TabularInline):
    """Inline view of code variations for EiPL submissions."""

    model = CodeVariation
    extra = 0
    fields = ("variation_index", "score", "tests_passed", "tests_total", "is_selected")
    readonly_fields = ("variation_index", "score", "tests_passed", "tests_total")


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    """Admin interface for submissions."""

    list_display = [
        "submission_id_short",
        "user",
        "problem",
        "submission_type",
        "score_display",
        "comprehension_level_display",
        "completion_status_display",
        "submitted_at",
    ]

    list_filter = [
        "submission_type",
        "execution_status",
        "completion_status",
        "comprehension_level",
        "is_correct",
        "passed_all_tests",
        "course",
        "problem_set",
        "submitted_at",
    ]

    search_fields = [
        "submission_id",
        "user__username",
        "user__email",
        "problem__title",
        "problem__slug",
    ]

    readonly_fields = [
        "submission_id",
        "submitted_at",
        "execution_time_ms",
        "memory_used_mb",
        "score",
        "passed_all_tests",
        "completion_status",
    ]

    fieldsets = (
        (
            "Identification",
            {"fields": ("submission_id", "user", "problem", "problem_set", "course")},
        ),
        (
            "Submission Details",
            {
                "fields": (
                    "submission_type",
                    "submitted_at",
                    "time_spent",
                    "raw_input",
                    "processed_code",
                )
            },
        ),
        (
            "Execution",
            {
                "fields": (
                    "execution_status",
                    "execution_time_ms",
                    "memory_used_mb",
                    "celery_task_id",
                )
            },
        ),
        (
            "Results",
            {
                "fields": (
                    "score",
                    "passed_all_tests",
                    "is_correct",
                    "completion_status",
                    "comprehension_level",
                )
            },
        ),
    )

    inlines = [TestExecutionInline, HintActivationInline, CodeVariationInline]

    def submission_id_short(self, obj):
        """Display shortened submission ID."""
        return str(obj.submission_id)[:8] + "..."

    submission_id_short.short_description = "ID"

    def score_display(self, obj):
        """Display score with color coding."""
        color = "green" if obj.score >= 80 else "orange" if obj.score >= 50 else "red"
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}%</span>', color, obj.score
        )

    score_display.short_description = "Score"

    def completion_status_display(self, obj):
        """Display completion status with icons."""
        icons = {"complete": "✅", "partial": "⚠️", "incomplete": "❌"}
        return format_html(
            "{} {}",
            icons.get(obj.completion_status, ""),
            obj.get_completion_status_display(),
        )

    completion_status_display.short_description = "Status"

    def comprehension_level_display(self, obj):
        """Display comprehension level with color coding."""
        if obj.comprehension_level == "high-level":
            color = "green"
            icon = "🎯"
            text = "High-level"
        elif obj.comprehension_level == "low-level":
            color = "orange"
            icon = "📝"
            text = "Low-level"
        else:
            color = "gray"
            icon = "⭕"
            text = "Not Evaluated"

        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color,
            icon,
            text,
        )

    comprehension_level_display.short_description = "Comprehension"


@admin.register(SegmentationAnalysis)
class SegmentationAnalysisAdmin(admin.ModelAdmin):
    """Admin interface for segmentation analysis."""

    list_display = [
        "submission_link",
        "comprehension_level_display",
        "segment_count",
        "confidence_score",
    ]

    list_filter = ["comprehension_level", "model_used"]

    search_fields = ["submission__submission_id", "submission__user__username"]

    readonly_fields = [
        "submission",
        "segment_count",
        "comprehension_level",
        "confidence_score",
        "processing_time_ms",
        "model_used",
    ]

    def submission_link(self, obj):
        """Link to parent submission."""
        return format_html(
            '<a href="/admin/submissions/submission/{}/change/">{}</a>',
            obj.submission.id,
            str(obj.submission.submission_id)[:8] + "...",
        )

    submission_link.short_description = "Submission"

    def comprehension_level_display(self, obj):
        """Display comprehension level with color."""
        color = "green" if obj.comprehension_level == "relational" else "orange"
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_comprehension_level_display(),
        )

    comprehension_level_display.short_description = "Comprehension"


@admin.register(SubmissionFeedback)
class SubmissionFeedbackAdmin(admin.ModelAdmin):
    """Admin interface for submission feedback."""

    list_display = [
        "submission_link",
        "feedback_type",
        "provided_by",
        "is_automated",
        "is_visible_to_student",
        "created_at",
    ]

    list_filter = [
        "feedback_type",
        "is_automated",
        "is_visible_to_student",
        "created_at",
    ]

    search_fields = [
        "submission__submission_id",
        "submission__user__username",
        "message",
    ]

    def submission_link(self, obj):
        """Link to parent submission."""
        return format_html(
            '<a href="/admin/submissions/submission/{}/change/">{}</a>',
            obj.submission.id,
            str(obj.submission.submission_id)[:8] + "...",
        )

    submission_link.short_description = "Submission"


@admin.register(ActivityEvent)
class ActivityEventAdmin(admin.ModelAdmin):
    """Read-only admin for activity event inspection."""

    list_display = [
        "event_type",
        "user",
        "problem",
        "course",
        "timestamp",
        "anonymous_user_id",
        "schema_version",
    ]

    list_filter = [
        "event_type",
        "schema_version",
        "course",
        "timestamp",
    ]

    search_fields = [
        "user__username",
        "anonymous_user_id",
        "event_type",
        "idempotency_key",
    ]

    readonly_fields = [
        "user",
        "event_type",
        "timestamp",
        "problem",
        "course",
        "payload",
        "anonymous_user_id",
        "schema_version",
        "idempotency_key",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# Register remaining models with basic admin
admin.site.register(TestExecution)
admin.site.register(HintActivation)
admin.site.register(CodeVariation)
