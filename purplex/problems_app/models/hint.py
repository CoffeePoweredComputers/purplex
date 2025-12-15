"""Problem hint configuration models."""

from django.core.exceptions import ValidationError
from django.db import models

from .base import Problem


class ProblemHint(models.Model):
    """Hint configuration for problems to support research on educational interventions."""

    HINT_TYPE_CHOICES = [
        ("variable_fade", "Variable Fade"),
        ("subgoal_highlight", "Subgoal Highlighting"),
        ("suggested_trace", "Suggested Trace"),
    ]

    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="hints")
    hint_type = models.CharField(max_length=20, choices=HINT_TYPE_CHOICES)
    is_enabled = models.BooleanField(default=False)
    min_attempts = models.IntegerField(
        default=3, help_text="Minimum attempts before hint is available"
    )
    content = models.JSONField(default=dict, help_text="Hint-specific configuration")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "problems_app"
        unique_together = ["problem", "hint_type"]
        ordering = ["hint_type"]

    def clean(self):
        """Validate content structure based on hint type."""
        if self.hint_type == "variable_fade":
            if "mappings" not in self.content:
                raise ValidationError("Variable fade hint must contain mappings")
            if not isinstance(self.content.get("mappings"), list):
                raise ValidationError("Mappings must be a list")
            for mapping in self.content.get("mappings", []):
                if (
                    not isinstance(mapping, dict)
                    or "from" not in mapping
                    or "to" not in mapping
                ):
                    raise ValidationError(
                        'Each mapping must have "from" and "to" fields'
                    )

        elif self.hint_type == "subgoal_highlight":
            if "subgoals" not in self.content:
                raise ValidationError("Subgoal highlight hint must contain subgoals")
            if not isinstance(self.content.get("subgoals"), list):
                raise ValidationError("Subgoals must be a list")
            for subgoal in self.content.get("subgoals", []):
                required_fields = ["line_start", "line_end", "title", "explanation"]
                if not all(field in subgoal for field in required_fields):
                    raise ValidationError(
                        f'Each subgoal must have: {", ".join(required_fields)}'
                    )

        elif self.hint_type == "suggested_trace":
            if "suggested_call" not in self.content:
                raise ValidationError(
                    "Suggested trace hint must contain suggested_call"
                )
            if not isinstance(self.content.get("suggested_call"), str):
                raise ValidationError("Suggested call must be a string")

    def __str__(self):
        return f"{self.problem.title} - {self.get_hint_type_display()}"
