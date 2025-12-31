"""TestCase model for problem test cases."""

import json

from django.core.exceptions import ValidationError
from django.db import models

from .base import Problem


class TestCase(models.Model):
    """Test case for validating problem solutions."""

    problem = models.ForeignKey(
        Problem, on_delete=models.CASCADE, related_name="test_cases"
    )
    inputs = models.JSONField(help_text="Array of input arguments")
    expected_output = models.JSONField(help_text="Expected output value")
    description = models.CharField(
        max_length=200, blank=True, help_text="Optional description for this test case"
    )
    is_hidden = models.BooleanField(
        default=False, help_text="Hidden test cases are not shown to students"
    )
    is_sample = models.BooleanField(
        default=False, help_text="Sample test cases are shown in problem description"
    )
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "problems_app"
        ordering = ["order", "id"]
        unique_together = ["problem", "order"]

    def clean(self):
        if not isinstance(self.inputs, list):
            raise ValidationError("Inputs must be a list of arguments")

        try:
            json.dumps(self.expected_output)
        except (TypeError, ValueError) as e:
            raise ValidationError("Expected output must be JSON serializable") from e

    def __str__(self):
        inputs_str = ", ".join(str(arg) for arg in self.inputs)
        return f"{self.problem.title} - Test {self.order}: f({inputs_str}) -> {self.expected_output}"
