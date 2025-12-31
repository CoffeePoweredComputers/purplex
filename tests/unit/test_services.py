"""
Test suite for all service layer components including segmentation.

Converted from Django TestCase to pytest style.
"""

from unittest.mock import MagicMock, patch

import pytest

from purplex.problems_app.services.ai_generation_service import AITestGenerationService
from purplex.problems_app.services.docker_execution_service import (
    DockerExecutionService as CodeExecutionService,
)
from purplex.problems_app.services.segmentation_service import SegmentationService
from purplex.problems_app.services.validation_service import ProblemValidationService

pytestmark = pytest.mark.unit


class TestServiceInitialization:
    """Tests for service layer component initialization."""

    def test_segmentation_service_initialization(self):
        """Test that SegmentationService initializes correctly."""
        service = SegmentationService()
        assert service is not None
        # Client should be None if API key not configured
        if not service.client:
            assert service.client is None

    def test_ai_service_initialization(self):
        """Test AITestGenerationService initialization."""
        service = AITestGenerationService()
        assert service is not None

    def test_code_execution_service(self):
        """Test CodeExecutionService basic functionality."""
        service = CodeExecutionService()
        assert service is not None
        assert service.max_execution_time == 5  # Default max execution time

    def test_validation_service(self):
        """Test ProblemValidationService initialization."""
        service = ProblemValidationService()
        assert service is not None


class TestSegmentationServiceVerbatim:
    """Tests for SegmentationService verbatim validation."""

    @pytest.fixture
    def service(self):
        """Provide a SegmentationService instance."""
        return SegmentationService()

    def test_verbatim_validation_integration(self, service):
        """Test verbatim validation is properly integrated."""
        user_prompt = "This function calculates the sum of two numbers"

        # Test segment validation
        valid_segment = "calculates the sum"
        invalid_segment = "computes the total"  # paraphrased

        assert service._validate_segment_is_verbatim(valid_segment, user_prompt)
        assert not service._validate_segment_is_verbatim(invalid_segment, user_prompt)

    def test_validate_segment_is_verbatim_exact_substring(self, service):
        """Test that verbatim validation correctly identifies exact substrings."""
        user_prompt = "This function adds two numbers together and returns their sum"

        # Test exact substring - should pass
        assert service._validate_segment_is_verbatim(
            "adds two numbers together", user_prompt
        )

        # Test with different punctuation - should fail
        assert not service._validate_segment_is_verbatim(
            "adds two numbers together.",  # Extra period
            user_prompt,
        )

        # Test paraphrased text - should fail
        assert not service._validate_segment_is_verbatim(
            "combines two values",  # Paraphrased
            user_prompt,
        )

        # Test exact match with spaces
        assert service._validate_segment_is_verbatim("returns their sum", user_prompt)

    @patch("openai.OpenAI")
    def test_segmentation_with_mock_api(self, mock_openai_class, service):
        """Test segmentation with mocked OpenAI API."""
        # Setup mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Mock API response - using non-overlapping lines for one-to-one mapping
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """
        {
            "segments": [
                {"id": 1, "text": "calculates the sum", "code_lines": [1]},
                {"id": 2, "text": "two numbers", "code_lines": [2]}
            ]
        }
        """
        mock_client.chat.completions.create.return_value = mock_response

        # Initialize service with mocked client
        service.client = mock_client

        # Test segmentation
        user_prompt = "This function calculates the sum of two numbers"
        reference_code = "def add(a, b):\n    return a + b"

        result = service.segment_prompt(
            user_prompt=user_prompt, reference_code=reference_code, problem_config={}
        )

        # Verify results
        assert result["success"]
        assert len(result["segments"]) == 2


class TestSegmentationPromptGeneration:
    """Test prompt generation for segmentation."""

    @pytest.fixture
    def service(self):
        """Provide a SegmentationService instance."""
        return SegmentationService()

    @pytest.fixture
    def reference_code(self):
        """Provide sample reference code."""
        return "def test():\n    pass"

    def test_prompt_includes_critical_rules(self, service, reference_code):
        """Test that generated prompts include one-to-one mapping rules."""
        prompt = service._create_segmentation_prompt(reference_code)

        # Check for critical one-to-one mapping elements (current format)
        assert "CRITICAL ONE-TO-ONE MAPPING RULES" in prompt
        assert "EXACTLY ONE distinct code section" in prompt
        assert "no overlapping" in prompt.lower()
        assert "ONE-TO-ONE MAPPING VALIDATION" in prompt

    def test_prompt_with_examples(self, service, reference_code):
        """Test prompt generation with custom examples."""
        examples = {
            "relational": {
                "prompt": "This is a test function",
                "segments": ["test function"],
                "code_lines": [[1, 2]],
            },
            "multi_structural": {
                "prompt": "Define function, then pass",
                "segments": ["Define function", "pass"],
                "code_lines": [[1], [2]],
            },
        }

        prompt = service._create_segmentation_prompt(reference_code, examples)

        # Check examples are included
        assert "SEGMENTATION EXAMPLES" in prompt
        assert "RELATIONAL" in prompt
        assert "MULTI-STRUCTURAL" in prompt
        assert examples["relational"]["prompt"] in prompt

    def test_prompt_no_function_definition_filtering(self, service, reference_code):
        """Test that the prompt does not include function definition filtering."""
        prompt = service._create_segmentation_prompt(reference_code)

        # Check that function definition filtering instruction is REMOVED
        assert (
            "Remove any segments that just describe function definition" not in prompt
        )


class TestSegmentParsing:
    """Tests for segment parsing and response format compatibility."""

    @pytest.fixture
    def service(self):
        """Provide a SegmentationService instance."""
        return SegmentationService()

    @pytest.fixture
    def reference_code(self):
        """Provide sample reference code."""
        return """def calculate_sum(a, b):
    result = a + b
    return result"""

    def test_parse_segments_returns_correct_format(self, service, reference_code):
        """Test that parsing returns segments in correct format."""
        user_prompt = "iterate through array and find sum"

        ai_response = """
        {
            "segments": [
                {"id": 1, "text": "iterate through array", "code_lines": [1]},
                {"id": 2, "text": "find sum", "code_lines": [2]}
            ]
        }
        """

        result = service._parse_segments(ai_response, reference_code, user_prompt)

        # Check segments format
        assert result["success"]
        assert "segments" in result
        assert len(result["segments"]) == 2

        # Verify segment structure
        for segment in result["segments"]:
            assert "id" in segment
            assert "text" in segment
            assert "code_lines" in segment
            assert isinstance(segment["code_lines"], list)

    def test_parse_segments_pure_segmentation(self, service, reference_code):
        """Test that _parse_segments returns segments with one-to-one mapping."""
        user_prompt = "The function takes two parameters and adds them to return"

        # Mock AI response - note: overlapping lines are deduplicated (one-to-one mapping)
        ai_response = """
        {
            "segments": [
                {"id": 1, "text": "takes two parameters", "code_lines": [1]},
                {"id": 2, "text": "combines the values", "code_lines": [2]},
                {"id": 3, "text": "return", "code_lines": [3]}
            ]
        }
        """

        result = service._parse_segments(ai_response, reference_code, user_prompt)

        # Should have all non-overlapping segments
        assert result["success"]
        assert len(result["segments"]) == 3  # 3 non-overlapping segments

        # Check that all segments are included
        segment_texts = [seg["text"] for seg in result["segments"]]
        assert "takes two parameters" in segment_texts
        assert "return" in segment_texts
        assert "combines the values" in segment_texts  # Non-verbatim also included

    def test_function_definition_segments_not_filtered(self, service, reference_code):
        """Test that function definition segments are NOT filtered (pure segmentation)."""
        user_prompt = "The function takes two numbers and returns their sum"

        ai_response = """
        {
            "segments": [
                {"id": 1, "text": "function takes two numbers", "code_lines": [1]},
                {"id": 2, "text": "returns their sum", "code_lines": [2]}
            ]
        }
        """

        result = service._parse_segments(ai_response, reference_code, user_prompt)

        # Both segments should be included even though first contains "function takes"
        assert result["success"]
        assert len(result["segments"]) == 2

        segment_texts = [seg["text"] for seg in result["segments"]]
        assert "function takes two numbers" in segment_texts  # Not filtered!
        assert "returns their sum" in segment_texts

    def test_segmentation_with_custom_examples(self, service, reference_code):
        """Test segmentation prompt with custom examples."""
        custom_examples = {
            "relational": {
                "prompt": "This function calculates the sum of two numbers",
                "segments": ["calculates the sum of two numbers"],
                "code_lines": [[1, 2, 3]],
            },
            "multi_structural": {
                "prompt": "First it takes parameters, then adds them, finally returns result",
                "segments": ["takes parameters", "adds them", "returns result"],
                "code_lines": [[1], [2], [3]],
            },
        }

        prompt = service._create_segmentation_prompt(reference_code, custom_examples)

        # Check that instructor examples are included (current format uses plain text headings)
        assert "SEGMENTATION EXAMPLES" in prompt
        assert "RELATIONAL" in prompt
        assert "MULTI-STRUCTURAL" in prompt
        assert custom_examples["relational"]["prompt"] in prompt
        assert custom_examples["multi_structural"]["prompt"] in prompt
