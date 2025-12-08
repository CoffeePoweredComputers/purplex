# Generated manually for adding Refute problem type

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("problems_app", "0016_refactor_spec_abstract_base"),
    ]

    operations = [
        migrations.CreateModel(
            name="RefuteProblem",
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
                (
                    "question_text",
                    models.TextField(help_text="The question/prompt shown to students"),
                ),
                (
                    "grading_mode",
                    models.CharField(
                        choices=[
                            ("deterministic", "Deterministic"),
                            ("llm", "LLM-graded"),
                            ("manual", "Manual"),
                        ],
                        default="deterministic",
                        max_length=20,
                    ),
                ),
                (
                    "claim_text",
                    models.TextField(
                        help_text="The false claim about the function (e.g., 'f(x) always returns positive')"
                    ),
                ),
                (
                    "reference_solution",
                    models.TextField(
                        help_text="The actual function code to execute against student input"
                    ),
                ),
                (
                    "function_signature",
                    models.TextField(
                        help_text="Function signature for input parsing (e.g., 'f(x: int) -> int')"
                    ),
                ),
                (
                    "expected_counterexample",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Optional known counterexample for hints (e.g., {'x': -5})",
                    ),
                ),
            ],
            options={
                "verbose_name": "Refute Problem",
                "verbose_name_plural": "Refute Problems",
            },
            bases=("problems_app.problem",),
        ),
    ]
