"""
Static problem types - problems with no code execution.

StaticProblem is the abstract base for:
- McqProblem (Multiple Choice)
- ShortAnswerProblem (future)
- EssayProblem (future)
"""
from django.db import models
from django.core.exceptions import ValidationError

from .base import Problem


class StaticProblem(Problem):
    """
    Abstract base for problems with no code execution.
    Pure question/answer format with deterministic or LLM grading.
    """

    GRADING_MODES = [
        ('deterministic', 'Deterministic'),
        ('llm', 'LLM-graded'),
        ('manual', 'Manual'),
    ]

    question_text = models.TextField(
        help_text="The question/prompt shown to students"
    )
    grading_mode = models.CharField(
        max_length=20,
        choices=GRADING_MODES,
        default='deterministic'
    )

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        if not self.question_text:
            raise ValidationError({
                'question_text': 'Question text is required'
            })


class McqProblem(StaticProblem):
    """
    Multiple Choice Question.

    Student selects from predefined options.
    Grading is deterministic (correct/incorrect).

    Option format:
    [
        {"id": "opt1", "text": "Option text", "is_correct": true, "explanation": "Why correct"},
        {"id": "opt2", "text": "Other option", "is_correct": false, "explanation": "Why wrong"},
    ]
    """

    options = models.JSONField(
        default=list,
        help_text="Array of {id, text, is_correct, explanation} objects"
    )
    allow_multiple = models.BooleanField(
        default=False,
        help_text="Allow selecting multiple answers"
    )
    shuffle_options = models.BooleanField(
        default=False,
        help_text="Randomize option order per attempt"
    )

    class Meta:
        app_label = 'problems_app'
        verbose_name = "MCQ Problem"
        verbose_name_plural = "MCQ Problems"

    @property
    def polymorphic_type(self) -> str:
        """Return type identifier for handler lookup."""
        return 'mcq'

    def clean(self):
        super().clean()

        # Validate options exist
        if not self.options or len(self.options) < 2:
            raise ValidationError({
                'options': 'At least 2 options required'
            })

        # Validate option structure
        for i, opt in enumerate(self.options):
            if not isinstance(opt, dict):
                raise ValidationError({
                    'options': f'Option {i+1} must be an object'
                })
            if not opt.get('id'):
                raise ValidationError({
                    'options': f'Option {i+1} must have an id'
                })
            if not opt.get('text', '').strip():
                raise ValidationError({
                    'options': f'Option {i+1} must have text'
                })

        # Validate correct answer count
        correct_count = sum(1 for opt in self.options if opt.get('is_correct'))

        if correct_count == 0:
            raise ValidationError({
                'options': 'At least one correct answer required'
            })

        if not self.allow_multiple and correct_count != 1:
            raise ValidationError({
                'options': 'Exactly one correct answer required (or enable allow_multiple)'
            })

    def __str__(self):
        return f"[MCQ] {self.title}"
