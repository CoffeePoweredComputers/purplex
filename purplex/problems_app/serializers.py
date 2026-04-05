from rest_framework import serializers
from rest_polymorphic.serializers import PolymorphicSerializer

from .handlers import get_handler, is_registered
from .models import (
    Course,
    CourseEnrollment,
    DebugFixProblem,
    EiplProblem,
    McqProblem,
    ProbeableCodeProblem,
    ProbeableSpecProblem,
    ProblemCategory,
    ProblemSet,
    PromptProblem,
    RefuteProblem,
    TestCase,
)
from .repositories import ProblemCategoryRepository, ProblemRepository
from .services.admin_service import AdminProblemService


class ProblemCategorySerializer(serializers.ModelSerializer):
    problems_count = serializers.ReadOnlyField()

    class Meta:
        model = ProblemCategory
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "icon",
            "color",
            "order",
            "problems_count",
        ]


class SimpleProblemSetSerializer(serializers.ModelSerializer):
    """Simple serializer for showing problem sets within problem details"""

    class Meta:
        model = ProblemSet
        fields = ["slug", "title"]


class TestCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCase
        fields = [
            "id",
            "inputs",
            "expected_output",
            "description",
            "is_hidden",
            "is_sample",
            "order",
        ]


class ProblemSerializer(serializers.ModelSerializer):
    """
    Base serializer for SpecProblem types (EiPL, Prompt).
    Note: MCQ problems should use McqProblemSerializer instead.
    """

    categories = ProblemCategorySerializer(many=True, read_only=True)
    category_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=ProblemCategoryRepository.get_all_queryset(),
        source="categories",
        write_only=True,
        required=False,
    )
    problem_sets = SimpleProblemSetSerializer(many=True, read_only=True)
    test_cases = TestCaseSerializer(many=True, read_only=True)
    test_cases_count = serializers.ReadOnlyField()
    visible_test_cases_count = serializers.ReadOnlyField()
    created_by_name = serializers.CharField(
        source="created_by.username", read_only=True
    )

    class Meta:
        model = EiplProblem  # Use EiplProblem as the concrete model
        fields = [
            "slug",
            "title",
            "description",
            "difficulty",
            "problem_type",
            "categories",
            "category_ids",
            "function_name",
            "function_signature",
            "reference_solution",
            "memory_limit",
            "tags",
            "is_active",
            "segmentation_enabled",
            "segmentation_config",
            "requires_highlevel_comprehension",
            "segmentation_threshold",
            "problem_sets",
            "test_cases",
            "test_cases_count",
            "visible_test_cases_count",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
            "version",
        ]
        read_only_fields = ["slug", "created_by", "created_at", "updated_at", "version"]


class McqProblemSerializer(serializers.ModelSerializer):
    """Serializer for MCQ problems using the polymorphic McqProblem model."""

    categories = ProblemCategorySerializer(many=True, read_only=True)
    category_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=ProblemCategoryRepository.get_all_queryset(),
        source="categories",
        write_only=True,
        required=False,
    )
    problem_sets = SimpleProblemSetSerializer(many=True, read_only=True)

    class Meta:
        model = McqProblem
        fields = [
            "slug",
            "title",
            "description",
            "difficulty",
            "problem_type",
            "categories",
            "category_ids",
            "tags",
            "is_active",
            "problem_sets",
            "created_by",
            "created_at",
            "updated_at",
            "version",
            # MCQ-specific fields
            "question_text",
            "grading_mode",
            "options",
            "allow_multiple",
            "shuffle_options",
        ]
        read_only_fields = [
            "slug",
            "problem_type",
            "created_by",
            "created_at",
            "updated_at",
            "version",
        ]

    def validate_options(self, value):
        """Validate MCQ options."""
        if not value or len(value) < 2:
            raise serializers.ValidationError("At least 2 options required")

        correct_count = 0
        seen_ids = set()
        for i, opt in enumerate(value):
            if not isinstance(opt, dict):
                raise serializers.ValidationError(f"Option {i + 1} must be an object")
            opt_id = opt.get("id")
            if not opt_id:
                raise serializers.ValidationError(f"Option {i + 1} must have an id")
            if opt_id in seen_ids:
                raise serializers.ValidationError(
                    f"Duplicate option id '{opt_id}' - each option must have a unique id"
                )
            seen_ids.add(opt_id)
            if not opt.get("text", "").strip():
                raise serializers.ValidationError(f"Option {i + 1} must have text")
            if opt.get("is_correct"):
                correct_count += 1

        if correct_count == 0:
            raise serializers.ValidationError("At least one correct answer required")

        return value

    def validate(self, attrs):
        """Validate allow_multiple vs correct count."""
        # Skip cross-field validation on partial updates — only validate
        # the relationship when both fields are being set together
        if self.partial and "options" not in attrs:
            return attrs

        options = attrs.get("options", [])
        allow_multiple = attrs.get(
            "allow_multiple",
            getattr(self.instance, "allow_multiple", False) if self.instance else False,
        )

        correct_count = sum(1 for opt in options if opt.get("is_correct"))
        if not allow_multiple and correct_count > 1:
            raise serializers.ValidationError(
                {
                    "options": "Multiple correct answers selected but allow_multiple is False"
                }
            )

        return attrs


class AdminMcqProblemSerializer(McqProblemSerializer):
    """Admin serializer for MCQ problems with full CRUD support."""

    category_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True,
    )

    class Meta(McqProblemSerializer.Meta):
        fields = McqProblemSerializer.Meta.fields + [
            "completion_threshold",
            "max_attempts",
        ]
        read_only_fields = ["slug", "created_at", "updated_at"]

    def create(self, validated_data):
        """Create MCQ problem."""
        from django.db import transaction

        category_ids = validated_data.pop("category_ids", [])

        with transaction.atomic():
            problem = ProblemRepository.create_mcq_problem(**validated_data)

            if category_ids:
                categories = ProblemCategoryRepository.get_categories_by_ids(
                    category_ids
                )
                problem.categories.set(categories)

            return problem

    def update(self, instance, validated_data):
        """Update MCQ problem."""
        from django.db import transaction

        category_ids = validated_data.pop("category_ids", None)

        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.version += 1
            instance.save()

            if category_ids is not None:
                categories = ProblemCategoryRepository.get_categories_by_ids(
                    category_ids
                )
                instance.categories.set(categories)

            return instance


class ProbeableCodeProblemSerializer(serializers.ModelSerializer):
    """Serializer for Probeable Code problems."""

    categories = ProblemCategorySerializer(many=True, read_only=True)
    category_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=ProblemCategoryRepository.get_all_queryset(),
        source="categories",
        write_only=True,
        required=False,
    )
    problem_sets = SimpleProblemSetSerializer(many=True, read_only=True)
    test_cases = TestCaseSerializer(many=True, read_only=True)
    test_cases_count = serializers.ReadOnlyField()
    visible_test_cases_count = serializers.ReadOnlyField()
    created_by_name = serializers.CharField(
        source="created_by.username", read_only=True
    )

    class Meta:
        model = ProbeableCodeProblem
        fields = [
            "slug",
            "title",
            "description",
            "difficulty",
            "problem_type",
            "categories",
            "category_ids",
            "function_name",
            "function_signature",
            "reference_solution",
            "memory_limit",
            "tags",
            "is_active",
            "segmentation_enabled",
            "segmentation_config",
            "requires_highlevel_comprehension",
            "segmentation_threshold",
            "problem_sets",
            "test_cases",
            "test_cases_count",
            "visible_test_cases_count",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
            "version",
            # ProbeableCode-specific fields
            "show_function_signature",
            "probe_mode",
            "max_probes",
            "cooldown_attempts",
            "cooldown_refill",
        ]
        read_only_fields = [
            "slug",
            "problem_type",
            "created_by",
            "created_at",
            "updated_at",
            "version",
        ]


class AdminProbeableCodeProblemSerializer(ProbeableCodeProblemSerializer):
    """Admin serializer for Probeable Code problems with full CRUD support."""

    category_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True,
    )
    test_cases = TestCaseSerializer(many=True, required=False)

    class Meta(ProbeableCodeProblemSerializer.Meta):
        read_only_fields = ["slug", "created_at", "updated_at"]

    def create(self, validated_data):
        """Create Probeable Code problem."""
        from django.db import transaction

        test_cases_data = validated_data.pop("test_cases", [])
        category_ids = validated_data.pop("category_ids", [])
        # Remove fields that are read-only properties
        validated_data.pop("problem_type", None)

        with transaction.atomic():
            problem = ProbeableCodeProblem.objects.create(**validated_data)

            if category_ids:
                categories = ProblemCategoryRepository.get_categories_by_ids(
                    category_ids
                )
                problem.categories.set(categories)

            # Create test cases
            for order, test_case_data in enumerate(test_cases_data):
                test_case_data["order"] = order
                TestCase.objects.create(problem=problem, **test_case_data)

            return problem

    def update(self, instance, validated_data):
        """Update Probeable Code problem."""
        from django.db import transaction

        test_cases_data = validated_data.pop("test_cases", None)
        category_ids = validated_data.pop("category_ids", None)

        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.version += 1
            instance.save()

            if category_ids is not None:
                categories = ProblemCategoryRepository.get_categories_by_ids(
                    category_ids
                )
                instance.categories.set(categories)

            if test_cases_data is not None:
                instance.test_cases.all().delete()
                for order, test_case_data in enumerate(test_cases_data):
                    test_case_data["order"] = order
                    TestCase.objects.create(problem=instance, **test_case_data)

            return instance


# ============================================================================
# Type-Specific Serializers for Problem Set Context
# ============================================================================


class HandlerConfigMixin:
    """Mixin for serializers that need handler-provided configuration."""

    def _get_handler_config(self, problem):
        """Get full config from handler, cached per serialization."""
        if not hasattr(self, "_handler_config_cache"):
            self._handler_config_cache = {}
        if problem.pk not in self._handler_config_cache:
            if is_registered(problem.problem_type):
                handler = get_handler(problem.problem_type)
                self._handler_config_cache[problem.pk] = handler.get_problem_config(
                    problem
                )
            else:
                self._handler_config_cache[problem.pk] = {}
        return self._handler_config_cache[problem.pk]

    def get_display_config(self, problem):
        """Get display configuration from handler."""
        return self._get_handler_config(problem).get("display", {})

    def get_input_config(self, problem):
        """Get input configuration from handler."""
        return self._get_handler_config(problem).get("input", {})

    def get_hints_config(self, problem):
        """Get hints configuration from handler."""
        return self._get_handler_config(problem).get("hints", {})

    def get_feedback_config(self, problem):
        """Get feedback configuration from handler."""
        return self._get_handler_config(problem).get("feedback", {})

    def get_probe_config(self, problem):
        """Get probe configuration from handler."""
        return self._get_handler_config(problem).get("probe", {})


# ============================================================================
# List Serializers (also need polymorphic handling)
# ============================================================================


class EiplProblemListSerializer(serializers.ModelSerializer):
    """List serializer for EiPL problems."""

    categories = ProblemCategorySerializer(many=True, read_only=True)
    problem_sets = SimpleProblemSetSerializer(many=True, read_only=True)
    test_cases_count = serializers.ReadOnlyField()

    class Meta:
        model = EiplProblem
        fields = [
            "slug",
            "title",
            "difficulty",
            "problem_type",
            "categories",
            "problem_sets",
            "function_name",
            "tags",
            "is_active",
            "test_cases_count",
            "created_at",
        ]


class PromptProblemListSerializer(serializers.ModelSerializer):
    """List serializer for Prompt problems."""

    categories = ProblemCategorySerializer(many=True, read_only=True)
    problem_sets = SimpleProblemSetSerializer(many=True, read_only=True)
    test_cases_count = serializers.ReadOnlyField()

    class Meta:
        model = PromptProblem
        fields = [
            "slug",
            "title",
            "difficulty",
            "problem_type",
            "categories",
            "problem_sets",
            "function_name",
            "display_mode",
            "image_url",
            "tags",
            "is_active",
            "test_cases_count",
            "created_at",
        ]


class McqProblemListSerializer(serializers.ModelSerializer):
    """List serializer for MCQ problems."""

    categories = ProblemCategorySerializer(many=True, read_only=True)
    problem_sets = SimpleProblemSetSerializer(many=True, read_only=True)

    class Meta:
        model = McqProblem
        fields = [
            "slug",
            "title",
            "difficulty",
            "problem_type",
            "categories",
            "problem_sets",
            "tags",
            "is_active",
            "created_at",
        ]


class RefuteProblemListSerializer(serializers.ModelSerializer):
    """List serializer for Refute (Counterexample) problems."""

    categories = ProblemCategorySerializer(many=True, read_only=True)
    problem_sets = SimpleProblemSetSerializer(many=True, read_only=True)

    class Meta:
        model = RefuteProblem
        fields = [
            "slug",
            "title",
            "difficulty",
            "problem_type",
            "categories",
            "problem_sets",
            "tags",
            "is_active",
            "created_at",
        ]


class RefuteProblemSerializer(serializers.ModelSerializer):
    """Full serializer for Refute (Counterexample) problems with all fields."""

    categories = ProblemCategorySerializer(many=True, read_only=True)
    category_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=ProblemCategoryRepository.get_all_queryset(),
        source="categories",
        write_only=True,
        required=False,
    )
    problem_sets = SimpleProblemSetSerializer(many=True, read_only=True)
    # question_text is inherited from StaticProblem but we auto-populate from claim_text
    question_text = serializers.CharField(required=False, allow_blank=True, default="")

    class Meta:
        model = RefuteProblem
        fields = [
            "slug",
            "title",
            "description",
            "difficulty",
            "problem_type",
            "categories",
            "category_ids",
            "problem_sets",
            "tags",
            "is_active",
            "created_by",
            "created_at",
            "updated_at",
            "version",
            # Refute-specific fields
            "question_text",
            "grading_mode",
            "claim_text",
            "claim_predicate",
            "reference_solution",
            "function_signature",
            "expected_counterexample",
        ]
        read_only_fields = ["slug", "created_by", "created_at", "updated_at", "version"]

    def validate_claim_text(self, value):
        """Validate claim text is provided."""
        if not value or not value.strip():
            raise serializers.ValidationError("Claim text is required")
        return value

    def validate_reference_solution(self, value):
        """Validate reference solution is provided."""
        if not value or not value.strip():
            raise serializers.ValidationError("Reference solution is required")
        return value

    def validate_function_signature(self, value):
        """Validate function signature is provided."""
        if not value or not value.strip():
            raise serializers.ValidationError("Function signature is required")
        return value


class AdminRefuteProblemSerializer(RefuteProblemSerializer):
    """Admin serializer for Refute problems with full CRUD support."""

    category_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True,
    )

    class Meta(RefuteProblemSerializer.Meta):
        fields = RefuteProblemSerializer.Meta.fields + [
            "completion_threshold",
            "max_attempts",
        ]
        read_only_fields = ["slug", "created_at", "updated_at"]

    def create(self, validated_data):
        """Create Refute problem."""
        from django.db import transaction

        category_ids = validated_data.pop("category_ids", [])

        # Auto-populate question_text from claim_text if not provided
        if not validated_data.get("question_text"):
            validated_data["question_text"] = validated_data.get("claim_text", "")

        with transaction.atomic():
            problem = RefuteProblem.objects.create(**validated_data)

            if category_ids:
                categories = ProblemCategoryRepository.get_categories_by_ids(
                    category_ids
                )
                problem.categories.set(categories)

            return problem

    def update(self, instance, validated_data):
        """Update Refute problem."""
        from django.db import transaction

        category_ids = validated_data.pop("category_ids", None)

        # Auto-populate question_text from claim_text if not provided
        if not validated_data.get("question_text") and validated_data.get("claim_text"):
            validated_data["question_text"] = validated_data.get("claim_text")

        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.version += 1
            instance.save()

            if category_ids is not None:
                categories = ProblemCategoryRepository.get_categories_by_ids(
                    category_ids
                )
                instance.categories.set(categories)

            return instance


class AdminPromptProblemSerializer(serializers.ModelSerializer):
    """Admin serializer for Prompt problems with full CRUD support."""

    categories = ProblemCategorySerializer(many=True, read_only=True)
    category_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True,
    )
    test_cases = TestCaseSerializer(many=True, required=False)
    display_mode = serializers.ChoiceField(
        choices=PromptProblem.DISPLAY_MODE_CHOICES,
        default="image",
    )
    display_data = serializers.JSONField(default=dict, required=False)
    image_url = serializers.URLField(required=False, allow_blank=True, default="")

    class Meta:
        model = PromptProblem
        fields = [
            "slug",
            "title",
            "description",
            "difficulty",
            "problem_type",
            "categories",
            "category_ids",
            "tags",
            "is_active",
            "created_by",
            "created_at",
            "updated_at",
            "version",
            # SpecProblem fields
            "reference_solution",
            "function_signature",
            "function_name",
            # Prompt-specific fields
            "display_mode",
            "display_data",
            "image_url",
            "image_alt_text",
            # Admin fields
            "test_cases",
            "completion_threshold",
            "max_attempts",
        ]
        read_only_fields = ["slug", "problem_type", "created_at", "updated_at"]

    def _resolve_display_mode(self):
        """Resolve display_mode for validation, respecting partial updates."""
        if "display_mode" in self.initial_data:
            return self.initial_data["display_mode"]
        if self.instance and self.partial:
            return self.instance.display_mode
        return "image"

    def validate_display_data(self, value):
        """Validate display_data structure based on display_mode."""
        display_mode = self._resolve_display_mode()

        if display_mode == "image":
            return value

        if not isinstance(value, dict):
            raise serializers.ValidationError("display_data must be an object")

        if display_mode == "terminal":
            runs = value.get("runs")
            if not runs or not isinstance(runs, list):
                raise serializers.ValidationError(
                    "Terminal mode requires a 'runs' array"
                )
            for i, run in enumerate(runs):
                if not isinstance(run, dict):
                    raise serializers.ValidationError(f"Run {i + 1} must be an object")
                interactions = run.get("interactions")
                if not interactions or not isinstance(interactions, list):
                    raise serializers.ValidationError(
                        f"Run {i + 1} must have an 'interactions' array"
                    )
                for j, interaction in enumerate(interactions):
                    if not isinstance(interaction, dict):
                        raise serializers.ValidationError(
                            f"Run {i + 1}, interaction {j + 1} must be an object"
                        )
                    if interaction.get("type") not in ("input", "output"):
                        raise serializers.ValidationError(
                            f"Run {i + 1}, interaction {j + 1}: "
                            "type must be 'input' or 'output'"
                        )
                    if not interaction.get("text", "").strip():
                        raise serializers.ValidationError(
                            f"Run {i + 1}, interaction {j + 1}: text must not be empty"
                        )

        elif display_mode == "function_table":
            calls = value.get("calls")
            if not calls or not isinstance(calls, list):
                raise serializers.ValidationError(
                    "Function table mode requires a 'calls' array"
                )
            for i, call in enumerate(calls):
                if not isinstance(call, dict):
                    raise serializers.ValidationError(f"Call {i + 1} must be an object")
                if "args" not in call or not isinstance(call["args"], list):
                    raise serializers.ValidationError(
                        f"Call {i + 1}: 'args' must be an array"
                    )
                if "return_value" not in call:
                    raise serializers.ValidationError(
                        f"Call {i + 1}: 'return_value' is required"
                    )

        return value

    def validate(self, attrs):
        """Cross-field validation: image_url required only for image mode."""
        attrs = super().validate(attrs)
        display_mode = attrs.get("display_mode") or self._resolve_display_mode()

        if display_mode == "image":
            if "image_url" in attrs:
                if not attrs["image_url"]:
                    raise serializers.ValidationError(
                        {"image_url": "Required when display_mode is 'image'"}
                    )
            elif not self.partial:
                raise serializers.ValidationError(
                    {"image_url": "Required when display_mode is 'image'"}
                )

        return attrs

    def create(self, validated_data):
        """Create Prompt problem."""
        from django.db import transaction

        test_cases_data = validated_data.pop("test_cases", [])
        category_ids = validated_data.pop("category_ids", [])
        validated_data.pop("problem_type", None)

        with transaction.atomic():
            problem = PromptProblem.objects.create(**validated_data)

            if category_ids:
                categories = ProblemCategoryRepository.get_categories_by_ids(
                    category_ids
                )
                problem.categories.set(categories)

            for order, test_case_data in enumerate(test_cases_data):
                test_case_data["order"] = order
                TestCase.objects.create(problem=problem, **test_case_data)

            return problem

    def update(self, instance, validated_data):
        """Update Prompt problem."""
        from django.db import transaction

        test_cases_data = validated_data.pop("test_cases", None)
        category_ids = validated_data.pop("category_ids", None)

        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.version += 1
            instance.save()

            if category_ids is not None:
                categories = ProblemCategoryRepository.get_categories_by_ids(
                    category_ids
                )
                instance.categories.set(categories)

            if test_cases_data is not None:
                instance.test_cases.all().delete()
                for order, test_case_data in enumerate(test_cases_data):
                    test_case_data["order"] = order
                    TestCase.objects.create(problem=instance, **test_case_data)

            return instance


class AdminDebugFixProblemSerializer(serializers.ModelSerializer):
    """Admin serializer for Debug Fix problems with full CRUD support."""

    categories = ProblemCategorySerializer(many=True, read_only=True)
    category_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True,
    )
    test_cases = TestCaseSerializer(many=True, required=False)

    class Meta:
        model = DebugFixProblem
        fields = [
            "slug",
            "title",
            "description",
            "difficulty",
            "problem_type",
            "categories",
            "category_ids",
            "tags",
            "is_active",
            "created_by",
            "created_at",
            "updated_at",
            "version",
            # SpecProblem fields
            "reference_solution",
            "function_signature",
            "function_name",
            # DebugFix-specific fields
            "buggy_code",
            "bug_hints",
            # Admin fields
            "test_cases",
            "completion_threshold",
            "max_attempts",
        ]
        read_only_fields = ["slug", "problem_type", "created_at", "updated_at"]

    def create(self, validated_data):
        """Create Debug Fix problem."""
        from django.db import transaction

        test_cases_data = validated_data.pop("test_cases", [])
        category_ids = validated_data.pop("category_ids", [])
        validated_data.pop("problem_type", None)

        with transaction.atomic():
            problem = DebugFixProblem.objects.create(**validated_data)

            if category_ids:
                categories = ProblemCategoryRepository.get_categories_by_ids(
                    category_ids
                )
                problem.categories.set(categories)

            for order, test_case_data in enumerate(test_cases_data):
                test_case_data["order"] = order
                TestCase.objects.create(problem=problem, **test_case_data)

            return problem

    def update(self, instance, validated_data):
        """Update Debug Fix problem."""
        from django.db import transaction

        test_cases_data = validated_data.pop("test_cases", None)
        category_ids = validated_data.pop("category_ids", None)

        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.version += 1
            instance.save()

            if category_ids is not None:
                categories = ProblemCategoryRepository.get_categories_by_ids(
                    category_ids
                )
                instance.categories.set(categories)

            if test_cases_data is not None:
                instance.test_cases.all().delete()
                for order, test_case_data in enumerate(test_cases_data):
                    test_case_data["order"] = order
                    TestCase.objects.create(problem=instance, **test_case_data)

            return instance


class AdminProbeableSpecProblemSerializer(serializers.ModelSerializer):
    """Admin serializer for Probeable Spec problems with full CRUD support."""

    categories = ProblemCategorySerializer(many=True, read_only=True)
    category_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True,
    )
    test_cases = TestCaseSerializer(many=True, required=False)

    class Meta:
        model = ProbeableSpecProblem
        fields = [
            "slug",
            "title",
            "description",
            "difficulty",
            "problem_type",
            "categories",
            "category_ids",
            "tags",
            "is_active",
            "created_by",
            "created_at",
            "updated_at",
            "version",
            # SpecProblem fields
            "reference_solution",
            "function_signature",
            "function_name",
            # ProbeableSpec-specific fields
            "show_function_signature",
            "probe_mode",
            "max_probes",
            "cooldown_attempts",
            "cooldown_refill",
            # Admin fields
            "test_cases",
            "completion_threshold",
            "max_attempts",
        ]
        read_only_fields = ["slug", "problem_type", "created_at", "updated_at"]

    def create(self, validated_data):
        """Create Probeable Spec problem."""
        from django.db import transaction

        test_cases_data = validated_data.pop("test_cases", [])
        category_ids = validated_data.pop("category_ids", [])
        validated_data.pop("problem_type", None)

        with transaction.atomic():
            problem = ProbeableSpecProblem.objects.create(**validated_data)

            if category_ids:
                categories = ProblemCategoryRepository.get_categories_by_ids(
                    category_ids
                )
                problem.categories.set(categories)

            for order, test_case_data in enumerate(test_cases_data):
                test_case_data["order"] = order
                TestCase.objects.create(problem=problem, **test_case_data)

            return problem

    def update(self, instance, validated_data):
        """Update Probeable Spec problem."""
        from django.db import transaction

        test_cases_data = validated_data.pop("test_cases", None)
        category_ids = validated_data.pop("category_ids", None)

        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.version += 1
            instance.save()

            if category_ids is not None:
                categories = ProblemCategoryRepository.get_categories_by_ids(
                    category_ids
                )
                instance.categories.set(categories)

            if test_cases_data is not None:
                instance.test_cases.all().delete()
                for order, test_case_data in enumerate(test_cases_data):
                    test_case_data["order"] = order
                    TestCase.objects.create(problem=instance, **test_case_data)

            return instance


class ProbeableCodeProblemListSerializer(serializers.ModelSerializer):
    """List serializer for Probeable Code problems."""

    categories = ProblemCategorySerializer(many=True, read_only=True)
    problem_sets = SimpleProblemSetSerializer(many=True, read_only=True)
    test_cases_count = serializers.ReadOnlyField()

    class Meta:
        model = ProbeableCodeProblem
        fields = [
            "slug",
            "title",
            "difficulty",
            "problem_type",
            "categories",
            "problem_sets",
            "function_name",
            "tags",
            "is_active",
            "test_cases_count",
            "created_at",
        ]


class DebugFixProblemListSerializer(serializers.ModelSerializer):
    """List serializer for Debug Fix problems."""

    categories = ProblemCategorySerializer(many=True, read_only=True)
    problem_sets = SimpleProblemSetSerializer(many=True, read_only=True)
    test_cases_count = serializers.ReadOnlyField()

    class Meta:
        model = DebugFixProblem
        fields = [
            "slug",
            "title",
            "difficulty",
            "problem_type",
            "categories",
            "problem_sets",
            "function_name",
            "tags",
            "is_active",
            "test_cases_count",
            "created_at",
        ]


class ProbeableSpecProblemListSerializer(serializers.ModelSerializer):
    """List serializer for Probeable Spec problems."""

    categories = ProblemCategorySerializer(many=True, read_only=True)
    problem_sets = SimpleProblemSetSerializer(many=True, read_only=True)
    test_cases_count = serializers.ReadOnlyField()

    class Meta:
        model = ProbeableSpecProblem
        fields = [
            "slug",
            "title",
            "difficulty",
            "problem_type",
            "categories",
            "problem_sets",
            "function_name",
            "tags",
            "is_active",
            "test_cases_count",
            "created_at",
        ]


class ProblemPolymorphicListSerializer(PolymorphicSerializer):
    """Polymorphic serializer for problem lists."""

    model_serializer_mapping = {
        EiplProblem: EiplProblemListSerializer,
        PromptProblem: PromptProblemListSerializer,
        McqProblem: McqProblemListSerializer,
        RefuteProblem: RefuteProblemListSerializer,
        ProbeableCodeProblem: ProbeableCodeProblemListSerializer,
        DebugFixProblem: DebugFixProblemListSerializer,
        ProbeableSpecProblem: ProbeableSpecProblemListSerializer,
    }


# Keep ProblemListSerializer for backward compatibility but use polymorphic internally
class ProblemListSerializer(serializers.Serializer):
    """
    List serializer that delegates to polymorphic serializer.
    Maintained for backward compatibility.
    """

    def to_representation(self, instance):
        # Delegate to polymorphic serializer
        serializer = ProblemPolymorphicListSerializer(instance, context=self.context)
        return serializer.data


class ProblemSetSerializer(serializers.ModelSerializer):
    """
    Serializer for ProblemSet.

    Note: problems_detail was removed because the view replaces it with
    service-layer data anyway. Use StudentService.get_problem_set_problems()
    for problem data with proper polymorphic resolution.
    """

    problems_count = serializers.ReadOnlyField()
    created_by_name = serializers.CharField(
        source="created_by.username", read_only=True
    )

    class Meta:
        model = ProblemSet
        fields = [
            "slug",
            "title",
            "description",
            "problems_count",
            "icon",
            "is_public",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["slug", "created_by", "created_at", "updated_at"]


class ProblemSetListSerializer(serializers.ModelSerializer):
    problems_count = serializers.ReadOnlyField()

    class Meta:
        model = ProblemSet
        fields = [
            "slug",
            "title",
            "description",
            "icon",
            "problems_count",
            "is_public",
            "created_at",
        ]


class AdminProblemSetSerializer(serializers.ModelSerializer):
    """
    Admin serializer for ProblemSet that includes problems_detail.

    Used by admin views that need to show/edit problems in a problem set.
    Uses service layer for problems_detail to avoid polymorphic serialization issues.
    """

    problems_count = serializers.ReadOnlyField()
    created_by_name = serializers.CharField(
        source="created_by.username", read_only=True
    )
    problems_detail = serializers.SerializerMethodField()

    class Meta:
        model = ProblemSet
        fields = [
            "slug",
            "title",
            "description",
            "problems_detail",
            "problems_count",
            "icon",
            "is_public",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["slug", "created_by", "created_at", "updated_at"]

    def get_problems_detail(self, obj):
        """
        Get problems in this set with minimal data for admin UI.

        Returns only fields needed by admin modal (slug, title, order, problem_type).
        Handles polymorphic resolution safely via polymorphic_ctype.
        """
        from .repositories import ProblemSetMembershipRepository

        memberships = ProblemSetMembershipRepository.get_problem_set_memberships(obj)
        result = []
        for m in memberships:
            # Get problem_type safely from polymorphic_ctype
            problem_type = "unknown"
            if hasattr(m.problem, "polymorphic_ctype") and m.problem.polymorphic_ctype:
                # Model name from content type, e.g. 'eiplproblem' -> 'eipl'
                model_name = m.problem.polymorphic_ctype.model
                # Map model names to problem types
                type_map = {
                    "eiplproblem": "eipl",
                    "mcqproblem": "mcq",
                    "promptproblem": "prompt",
                    "refuteproblem": "refute",
                    "debugfixproblem": "debug_fix",
                    "probeablecodeproblem": "probeable_code",
                    "probeablespecproblem": "probeable_spec",
                }
                problem_type = type_map.get(model_name, model_name)

            result.append(
                {
                    "order": m.order,
                    "problem": {
                        "slug": m.problem.slug,
                        "title": m.problem.title,
                        "problem_type": problem_type,
                    },
                }
            )
        return result


# Admin-specific serializers with more control
class AdminProblemSerializer(ProblemSerializer):
    """Enhanced serializer for admin problem operations with test case handling"""

    # Read-only fields
    categories = serializers.SerializerMethodField()
    test_cases_count = serializers.ReadOnlyField()
    visible_test_cases_count = serializers.ReadOnlyField()
    created_by_name = serializers.CharField(
        source="created_by.username", read_only=True
    )

    # Write-only fields
    category_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True,
    )

    # Test cases handling
    test_cases = TestCaseSerializer(many=True, required=False)

    class Meta(ProblemSerializer.Meta):
        read_only_fields = ["created_at", "updated_at"]

    def get_categories(self, obj):
        """Get categories with proper serialization"""
        return ProblemCategorySerializer(obj.categories.all(), many=True).data

    def validate(self, attrs):
        """Comprehensive validation using validation service.

        Note: MCQ problems should use McqProblemSerializer, not this serializer.
        This serializer is for EiPL/Prompt problems only.
        """
        import logging

        logger = logging.getLogger(__name__)

        try:
            from .services.validation_service import ProblemValidationService

            validation_service = ProblemValidationService()

            # Skip full validation on partial updates — only validate provided fields
            if self.partial:
                return attrs

            # Validate problem data - returns (is_valid, error_message)
            is_valid, error_message = validation_service.validate_problem_data(attrs)
            if not is_valid:
                # Validation service returns a single error message string
                # Try to determine which field the error relates to
                field = "non_field_errors"
                if error_message:
                    # Extract field name if present in error message
                    if error_message.lower().startswith("title"):
                        field = "title"
                    elif error_message.lower().startswith("description"):
                        field = "description"
                    elif "reference_solution" in error_message.lower():
                        field = "reference_solution"
                    elif "function_signature" in error_message.lower():
                        field = "function_signature"
                    elif "function_name" in error_message.lower():
                        field = "function_name"
                raise serializers.ValidationError(
                    {field: [error_message or "Validation failed"]}
                )

            return attrs
        except serializers.ValidationError:
            raise  # Re-raise validation errors
        except Exception as e:
            # Log the error for debugging but don't fail validation
            logger.warning(f"Validation service error: {str(e)}")

            # Perform basic validation instead
            # On partial updates, only validate fields that are present in attrs
            is_partial = self.partial

            if "title" in attrs and not attrs["title"].strip():
                raise serializers.ValidationError(
                    {"title": ["Title is required"]}
                ) from None
            elif not is_partial and not attrs.get("title", "").strip():
                raise serializers.ValidationError(
                    {"title": ["Title is required"]}
                ) from None

            # Reference solution is required for EiPL/Prompt problems (create only)
            if (
                "reference_solution" in attrs
                and not attrs["reference_solution"].strip()
            ):
                raise serializers.ValidationError(
                    {"reference_solution": ["Reference solution is required"]}
                ) from None
            elif not is_partial and not attrs.get("reference_solution", "").strip():
                raise serializers.ValidationError(
                    {"reference_solution": ["Reference solution is required"]}
                ) from None

            return attrs

    def create(self, validated_data):
        """Create problem with test cases in a transaction"""
        import re

        from django.db import transaction

        test_cases_data = validated_data.pop("test_cases", [])
        category_ids = validated_data.pop("category_ids", [])

        # Auto-extract function_name from reference_solution if not provided
        # function_signature is now required and must be provided explicitly for test case parsing
        reference_solution = validated_data.get("reference_solution", "")
        if reference_solution:
            # Extract function_name if not provided
            if not validated_data.get("function_name"):
                func_name_match = re.match(r"def\s+(\w+)\s*\(", reference_solution)
                if func_name_match:
                    validated_data["function_name"] = func_name_match.group(1)

        # Description is optional for EiPL/Prompt problems
        if "description" not in validated_data or not validated_data["description"]:
            validated_data["description"] = ""

        # Automatically set requires_highlevel_comprehension for EiPL problems with segmentation
        if validated_data.get("problem_type") == "eipl":
            segmentation_config = validated_data.get("segmentation_config", {})
            # If segmentation is enabled (or not explicitly disabled), require high-level comprehension
            if segmentation_config.get("enabled", True):
                validated_data["requires_highlevel_comprehension"] = True
            else:
                validated_data["requires_highlevel_comprehension"] = False

        with transaction.atomic():
            # Create EiplProblem directly (not via service which uses base Problem)
            problem = EiplProblem.objects.create(**validated_data)

            # Set categories using service
            if category_ids:
                categories = AdminProblemService.get_categories_by_ids(category_ids)
                problem.categories.set(categories)

            # Create test cases using service
            for order, test_case_data in enumerate(test_cases_data):
                test_case_data["order"] = order
                AdminProblemService.create_test_case(problem, test_case_data)

            return problem

    def update(self, instance, validated_data):
        """Update problem with test cases in a transaction"""
        import re

        from django.db import transaction

        test_cases_data = validated_data.pop("test_cases", None)
        category_ids = validated_data.pop("category_ids", None)

        # Auto-extract function_name from reference_solution if not provided
        # function_signature is now required and must be provided explicitly for test case parsing
        reference_solution = validated_data.get(
            "reference_solution", instance.reference_solution
        )
        if reference_solution:
            # Extract function_name if not provided
            if "function_name" not in validated_data or not validated_data.get(
                "function_name"
            ):
                func_name_match = re.match(r"def\s+(\w+)\s*\(", reference_solution)
                if func_name_match:
                    validated_data["function_name"] = func_name_match.group(1)

        # Automatically set requires_highlevel_comprehension for EiPL problems with segmentation
        problem_type = validated_data.get("problem_type", instance.problem_type)
        if problem_type == "eipl":
            segmentation_config = validated_data.get(
                "segmentation_config", instance.segmentation_config
            )
            # If segmentation is enabled (or not explicitly disabled), require high-level comprehension
            if segmentation_config.get("enabled", True):
                validated_data["requires_highlevel_comprehension"] = True
            else:
                validated_data["requires_highlevel_comprehension"] = False

        with transaction.atomic():
            # Update problem fields
            for attr, value in validated_data.items():
                setattr(instance, attr, value)

            # Increment version
            instance.version += 1
            instance.save()

            # Update categories if provided using service
            if category_ids is not None:
                categories = AdminProblemService.get_categories_by_ids(category_ids)
                instance.categories.set(categories)

            # Update test cases if provided
            if test_cases_data is not None:
                # Delete existing test cases
                instance.test_cases.all().delete()

                # Create new test cases using service
                for order, test_case_data in enumerate(test_cases_data):
                    test_case_data["order"] = order
                    AdminProblemService.create_test_case(instance, test_case_data)

            return instance

    def to_representation(self, instance):
        """Custom representation with proper test case serialization"""
        data = super().to_representation(instance)

        # Include test cases with proper serialization
        test_cases = instance.test_cases.all().order_by("order")
        data["test_cases"] = TestCaseSerializer(test_cases, many=True).data

        return data


# Course-related serializers


class CourseInstructorSerializer(serializers.Serializer):
    """Serializer for CourseInstructor (read)."""

    user_id = serializers.IntegerField(source="user.id")
    username = serializers.CharField(source="user.username")
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField(source="user.email")
    role = serializers.CharField()
    added_at = serializers.DateTimeField()

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


class CourseInstructorCreateSerializer(serializers.Serializer):
    """Serializer for adding an instructor to a course."""

    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=["primary", "ta"], default="primary")


class CourseListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing courses"""

    instructor_name = serializers.SerializerMethodField()
    problem_sets_count = serializers.IntegerField(read_only=True)
    enrolled_students_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Course
        fields = [
            "id",
            "course_id",
            "slug",
            "name",
            "description",
            "instructor_name",
            "problem_sets_count",
            "enrolled_students_count",
            "is_active",
            "enrollment_open",
            "created_at",
        ]

    def get_instructor_name(self, obj):
        """Get comma-joined primary instructor names."""
        if hasattr(obj, "course_instructors"):
            primaries = [
                ci for ci in obj.course_instructors.all() if ci.role == "primary"
            ]
            names = [ci.user.get_full_name() or ci.user.username for ci in primaries]
            if names:
                return ", ".join(names)
        return "Unknown Instructor"


class InstructorCourseListSerializer(serializers.Serializer):
    """Serializer for instructor course list endpoint.

    Works with dictionaries returned by CourseRepository.get_instructor_courses_with_stats().
    """

    id = serializers.IntegerField()
    course_id = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    instructor_name = serializers.CharField()
    is_active = serializers.BooleanField()
    enrollment_open = serializers.BooleanField()
    problem_sets_count = serializers.IntegerField()
    enrolled_students_count = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    my_role = serializers.CharField(required=False, allow_null=True)


class CourseDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for course with problem sets"""

    instructors = serializers.SerializerMethodField()
    problem_sets = serializers.SerializerMethodField()
    enrolled_students_count = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "course_id",
            "slug",
            "name",
            "description",
            "instructors",
            "problem_sets",
            "enrolled_students_count",
            "is_active",
            "enrollment_open",
            "created_at",
            "updated_at",
        ]

    def get_enrolled_students_count(self, obj):
        return obj.enrollments.filter(is_active=True).count()

    def get_instructors(self, obj):
        """Multi-instructor list from CourseInstructor table."""
        course_instructors = obj.course_instructors.select_related("user").order_by(
            "role", "added_at"
        )
        return CourseInstructorSerializer(course_instructors, many=True).data

    def get_problem_sets(self, obj):
        """Get problem sets ordered by position in course"""
        course_problem_sets = obj.courseproblemset_set.select_related(
            "problem_set"
        ).order_by("order")
        return [
            {
                "id": cps.id,
                "order": cps.order,
                "is_required": cps.is_required,
                "due_date": cps.due_date.isoformat() if cps.due_date else None,
                "deadline_type": cps.deadline_type,
                "problem_set": ProblemSetListSerializer(cps.problem_set).data,
            }
            for cps in course_problem_sets
        ]


class CourseCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating courses"""

    instructor_id = serializers.IntegerField(write_only=True, required=False)
    problem_set_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )

    class Meta:
        model = Course
        fields = [
            "course_id",
            "name",
            "description",
            "instructor_id",
            "is_active",
            "enrollment_open",
            "problem_set_ids",
        ]

    def validate_course_id(self, value):
        """Validate course ID format"""
        if not value:
            raise serializers.ValidationError("Course ID is required")

        # Check format (alphanumeric with hyphens/underscores)
        import re

        if not re.match(r"^[A-Za-z0-9_-]+$", value):
            raise serializers.ValidationError(
                "Course ID can only contain letters, numbers, hyphens, and underscores"
            )

        # Check uniqueness using service (exclude current instance for updates)
        if self.instance:
            # For updates, check if another course has this ID
            exists = AdminProblemService.check_course_exists(value)
            if exists and self.instance.course_id != value:
                raise serializers.ValidationError(
                    "A course with this ID already exists"
                )
        else:
            # For creation, check if any course has this ID
            if AdminProblemService.check_course_exists(value):
                raise serializers.ValidationError(
                    "A course with this ID already exists"
                )

        return value

    def create(self, validated_data):
        problem_set_ids = validated_data.pop("problem_set_ids", [])
        validated_data.pop("instructor_id", None)
        # Create course using service
        course = AdminProblemService.create_course(validated_data)

        # Add problem sets with ordering using service
        for order, ps_id in enumerate(problem_set_ids):
            problem_set = AdminProblemService.get_problem_set_by_id(ps_id)
            if problem_set:
                AdminProblemService.create_course_problem_set(
                    course=course, problem_set=problem_set, order=order
                )

        return course

    def update(self, instance, validated_data):
        problem_set_ids = validated_data.pop("problem_set_ids", None)
        validated_data.pop("instructor_id", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update problem sets if provided
        if problem_set_ids is not None:
            # Clear existing
            instance.courseproblemset_set.all().delete()

            # Add new ones using service
            for order, ps_id in enumerate(problem_set_ids):
                problem_set = AdminProblemService.get_problem_set_by_id(ps_id)
                if problem_set:
                    AdminProblemService.create_course_problem_set(
                        course=instance, problem_set=problem_set, order=order
                    )

        return instance


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying course enrollments (students in a course).
    Data minimization (GDPR Art. 25): Only shows username by default.
    Email/name only included if the student hasn't opted out of
    directory information (FERPA opt-out).
    """

    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()

    class Meta:
        model = CourseEnrollment
        fields = [
            "id",
            "user_id",
            "username",
            "email",
            "first_name",
            "last_name",
            "enrolled_at",
            "is_active",
        ]
        read_only_fields = fields

    def _is_directory_visible(self, obj):
        """Check if user has opted into directory information visibility."""
        profile = getattr(obj.user, "profile", None)
        if profile is None:
            return True  # Default to visible if no profile
        return profile.directory_info_visible

    def get_email(self, obj):
        if self._is_directory_visible(obj):
            return obj.user.email
        return None

    def get_first_name(self, obj):
        if self._is_directory_visible(obj):
            return obj.user.first_name
        return None

    def get_last_name(self, obj):
        if self._is_directory_visible(obj):
            return obj.user.last_name
        return None


class CourseLookupSerializer(serializers.Serializer):
    """Serializer for looking up a course by ID for enrollment"""

    course_id = serializers.CharField(max_length=50)

    def validate_course_id(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Course ID is required")
        return value.strip()


class CourseEnrollSerializer(serializers.Serializer):
    """Serializer for enrolling in a course"""

    course_id = serializers.CharField(max_length=50)

    def validate_course_id(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Course ID is required")
        return value.strip()
