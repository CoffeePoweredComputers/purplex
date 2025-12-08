# Migration: Add ProbeableCodeProblem model

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("problems_app", "0018_add_debugfix_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProbeableCodeProblem",
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
                        help_text="Reference implementation for test validation (oracle code)"
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
                # ProbeableCodeProblem-specific fields
                (
                    "show_function_signature",
                    models.BooleanField(
                        default=True,
                        help_text="Show function parameters/types to student",
                    ),
                ),
                (
                    "probe_mode",
                    models.CharField(
                        choices=[
                            ("block", "Block after limit"),
                            ("cooldown", "Cooldown refill"),
                            ("explore", "Unlimited"),
                        ],
                        default="explore",
                        help_text="How probe limits are enforced",
                        max_length=20,
                    ),
                ),
                (
                    "max_probes",
                    models.PositiveIntegerField(
                        default=10,
                        help_text="Initial probe budget (ignored for 'explore' mode)",
                    ),
                ),
                (
                    "cooldown_attempts",
                    models.PositiveIntegerField(
                        default=3,
                        help_text="Submission attempts required before probe refill (cooldown mode only)",
                    ),
                ),
                (
                    "cooldown_refill",
                    models.PositiveIntegerField(
                        default=5,
                        help_text="Number of probes granted after cooldown (cooldown mode only)",
                    ),
                ),
            ],
            options={
                "verbose_name": "Probeable Code Problem",
                "verbose_name_plural": "Probeable Code Problems",
            },
            bases=("problems_app.problem",),
        ),
    ]
