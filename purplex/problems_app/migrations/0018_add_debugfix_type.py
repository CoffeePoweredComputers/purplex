# Migration: Add DebugFixProblem model

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("problems_app", "0017_add_refute_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="DebugFixProblem",
            fields=[
                (
                    "problem_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="problems_app.problem",
                    ),
                ),
                # SpecProblem fields (since SpecProblem is abstract)
                (
                    "reference_solution",
                    models.TextField(
                        help_text="Reference implementation for test validation"
                    ),
                ),
                (
                    "function_signature",
                    models.TextField(
                        help_text="Function signature with type hints for test case parsing"
                    ),
                ),
                (
                    "function_name",
                    models.CharField(
                        blank=True,
                        max_length=50,
                        help_text="Auto-extracted from reference_solution if not provided",
                    ),
                ),
                (
                    "memory_limit",
                    models.PositiveIntegerField(
                        default=128,
                        help_text="Memory limit in MB for code execution",
                    ),
                ),
                (
                    "llm_config",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="LLM settings: {model, temperature, max_tokens}",
                    ),
                ),
                (
                    "segmentation_config",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Segmentation settings: {enabled, min_segments, examples}",
                    ),
                ),
                (
                    "segmentation_threshold",
                    models.PositiveIntegerField(
                        default=2,
                        help_text="Max segments for high-level comprehension (fewer = better)",
                    ),
                ),
                (
                    "requires_highlevel_comprehension",
                    models.BooleanField(
                        default=True,
                        help_text="Require high-level comprehension for full credit",
                    ),
                ),
                # DebugFixProblem-specific fields
                (
                    "buggy_code",
                    models.TextField(
                        help_text="Code with intentional bug(s) for student to fix"
                    ),
                ),
                (
                    "bug_hints",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Progressive hints: [{level: 1, text: 'Check line 5'}, ...]",
                    ),
                ),
                (
                    "allow_complete_rewrite",
                    models.BooleanField(
                        default=True,
                        help_text="If False, require minimal diff from buggy_code",
                    ),
                ),
            ],
            options={
                "verbose_name": "Debug Fix Problem",
                "verbose_name_plural": "Debug Fix Problems",
            },
            bases=("problems_app.problem",),
        ),
    ]
