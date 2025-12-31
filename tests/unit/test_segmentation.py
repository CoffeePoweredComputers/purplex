"""Unit tests for SegmentationService.

Tests the prompt segmentation functionality used for EiPL submissions.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from purplex.problems_app.services.segmentation_service import SegmentationService


@pytest.fixture
def segmentation_service():
    """Create a SegmentationService instance with mocked AI clients."""
    with patch.object(SegmentationService, "__init__", lambda self: None):
        service = SegmentationService()
        service.provider = "openai"
        service.client = MagicMock()
        service.model_name = "gpt-4o-mini"
        service.openai_client = MagicMock()
        service.llama_client = None
        return service


@pytest.fixture
def sample_code():
    """Sample Python code for segmentation tests."""
    return """def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)"""


class TestDetermineComprehensionLevel:
    """Tests for _determine_comprehension_level method."""

    def test_relational_with_one_segment(self, segmentation_service):
        """Single segment should be classified as relational."""
        level, feedback = segmentation_service._determine_comprehension_level(
            segment_count=1, threshold=2
        )
        assert level == "relational"
        assert "1 segment" in feedback

    def test_relational_at_threshold(self, segmentation_service):
        """Segment count at threshold should be relational."""
        level, feedback = segmentation_service._determine_comprehension_level(
            segment_count=2, threshold=2
        )
        assert level == "relational"

    def test_multi_structural_above_threshold(self, segmentation_service):
        """Segment count above threshold should be multi_structural."""
        level, feedback = segmentation_service._determine_comprehension_level(
            segment_count=3, threshold=2
        )
        assert level == "multi_structural"
        assert "too detailed" in feedback.lower()

    def test_custom_threshold(self, segmentation_service):
        """Custom threshold should be respected."""
        level, _ = segmentation_service._determine_comprehension_level(
            segment_count=4, threshold=5
        )
        assert level == "relational"

    def test_custom_feedback_messages(self, segmentation_service):
        """Custom feedback messages should be used when provided."""
        config = {
            "feedback_messages": {
                "relational": "Great job!",
                "multi_structural": "Try again.",
            }
        }
        level, feedback = segmentation_service._determine_comprehension_level(
            segment_count=1, threshold=2, config=config
        )
        assert feedback == "Great job!"


class TestValidateSegmentVerbatim:
    """Tests for _validate_segment_is_verbatim method."""

    def test_exact_match(self, segmentation_service):
        """Exact substring should return True."""
        user_prompt = "The function calculates factorial recursively."
        segment_text = "calculates factorial"
        assert segmentation_service._validate_segment_is_verbatim(
            segment_text, user_prompt
        )

    def test_full_prompt_match(self, segmentation_service):
        """Full prompt as segment should return True."""
        user_prompt = "The function calculates factorial."
        assert segmentation_service._validate_segment_is_verbatim(
            user_prompt, user_prompt
        )

    def test_no_match(self, segmentation_service):
        """Non-existent text should return False."""
        user_prompt = "The function calculates factorial."
        segment_text = "computes recursion"
        assert not segmentation_service._validate_segment_is_verbatim(
            segment_text, user_prompt
        )

    def test_empty_segment(self, segmentation_service):
        """Empty segment should return False."""
        user_prompt = "The function calculates factorial."
        assert not segmentation_service._validate_segment_is_verbatim("", user_prompt)

    def test_whitespace_handling(self, segmentation_service):
        """Whitespace should be stripped from segment."""
        user_prompt = "The function calculates factorial."
        segment_text = "  calculates factorial  "
        # After stripping, should match
        assert segmentation_service._validate_segment_is_verbatim(
            segment_text, user_prompt
        )


class TestParseSegments:
    """Tests for _parse_segments method."""

    def test_valid_json_response(self, segmentation_service, sample_code):
        """Valid JSON with segments should be parsed correctly."""
        ai_response = json.dumps(
            {
                "segments": [
                    {"id": 1, "text": "base case", "code_lines": [2, 3]},
                    {"id": 2, "text": "recursive call", "code_lines": [4]},
                ]
            }
        )
        result = segmentation_service._parse_segments(
            ai_response, sample_code, "base case and recursive call"
        )
        assert result["success"]
        assert len(result["segments"]) == 2
        assert result["segments"][0]["code_lines"] == [2, 3]

    def test_overlapping_lines_rejected(self, segmentation_service, sample_code):
        """Segments with overlapping lines should have duplicates removed."""
        ai_response = json.dumps(
            {
                "segments": [
                    {"id": 1, "text": "first segment", "code_lines": [1, 2]},
                    {"id": 2, "text": "second segment", "code_lines": [2, 3]},
                ]
            }
        )
        result = segmentation_service._parse_segments(
            ai_response, sample_code, "first second"
        )
        assert result["success"]
        # Line 2 should only appear in first segment
        all_lines = []
        for segment in result["segments"]:
            all_lines.extend(segment["code_lines"])
        # Line 2 should appear exactly once
        assert all_lines.count(2) == 1

    def test_invalid_line_numbers_filtered(self, segmentation_service, sample_code):
        """Invalid line numbers (out of range) should be filtered out."""
        ai_response = json.dumps(
            {"segments": [{"id": 1, "text": "segment", "code_lines": [1, 100, -1, 2]}]}
        )
        result = segmentation_service._parse_segments(
            ai_response, sample_code, "segment"
        )
        assert result["success"]
        # Only valid lines (1-4) should be kept
        assert 100 not in result["segments"][0]["code_lines"]
        assert -1 not in result["segments"][0]["code_lines"]

    def test_empty_segments_response(self, segmentation_service, sample_code):
        """Response with no segments should fail gracefully."""
        ai_response = json.dumps({"segments": []})
        result = segmentation_service._parse_segments(ai_response, sample_code, "test")
        assert not result["success"]
        assert "No segments found" in result["error"]

    def test_invalid_json_response(self, segmentation_service, sample_code):
        """Invalid JSON should return error."""
        ai_response = "not valid json"
        result = segmentation_service._parse_segments(ai_response, sample_code, "test")
        assert not result["success"]
        assert "JSON parsing error" in result["error"]

    def test_groups_format_generated(self, segmentation_service, sample_code):
        """EiPL Grader format (groups) should be generated alongside segments."""
        ai_response = json.dumps(
            {"segments": [{"id": 1, "text": "base case", "code_lines": [2, 3]}]}
        )
        result = segmentation_service._parse_segments(
            ai_response, sample_code, "base case"
        )
        assert result["success"]
        assert "groups" in result
        assert len(result["groups"]) == 1
        assert "explanation_portion" in result["groups"][0]
        assert "code" in result["groups"][0]


class TestCreateSegmentationPrompt:
    """Tests for _create_segmentation_prompt method."""

    def test_includes_reference_code(self, segmentation_service):
        """Prompt should include the reference code."""
        code = "print('hello')"
        prompt = segmentation_service._create_segmentation_prompt(code)
        assert code in prompt

    def test_includes_custom_examples(self, segmentation_service):
        """Custom examples should be included in prompt."""
        code = "print('hello')"
        examples = {
            "relational": {
                "prompt": "prints hello",
                "segments": ["prints hello"],
                "code_lines": [[1]],
            }
        }
        prompt = segmentation_service._create_segmentation_prompt(code, examples)
        assert "prints hello" in prompt

    def test_json_format_instructions(self, segmentation_service):
        """Prompt should include JSON format instructions."""
        code = "print('hello')"
        prompt = segmentation_service._create_segmentation_prompt(code)
        assert '"segments"' in prompt
        assert "JSON" in prompt


class TestSegmentPrompt:
    """Tests for the main segment_prompt method."""

    def test_returns_error_when_no_client(self, segmentation_service):
        """Should return error when no AI client is configured."""
        segmentation_service.client = None
        result = segmentation_service.segment_prompt("test prompt", "test code")
        assert not result["success"]
        assert "No AI provider configured" in result["error"]

    def test_successful_segmentation(self, segmentation_service, sample_code):
        """Should return successful result with valid AI response."""
        # Mock the AI call
        mock_response = json.dumps(
            {
                "segments": [
                    {"id": 1, "text": "factorial function", "code_lines": [1, 4]}
                ]
            }
        )
        segmentation_service._call_ai = MagicMock(return_value=mock_response)
        segmentation_service._log_segmentation_debug = MagicMock()
        segmentation_service._log_segmentation_result = MagicMock()

        result = segmentation_service.segment_prompt(
            "factorial function", sample_code, {"threshold": 2}
        )

        assert result["success"]
        assert result["segment_count"] == 1
        assert result["comprehension_level"] == "relational"
        assert result["processing_time"] > 0

    def test_handles_ai_exception(self, segmentation_service, sample_code):
        """Should handle AI call exceptions gracefully."""
        segmentation_service._call_ai = MagicMock(side_effect=Exception("API error"))

        result = segmentation_service.segment_prompt(
            "test prompt", sample_code, {"threshold": 2}
        )

        assert not result["success"]
        assert "API error" in result["error"]


@pytest.mark.unit
class TestIsValidExample:
    """Tests for _is_valid_example method."""

    def test_valid_example(self, segmentation_service):
        """Example with all required fields should be valid."""
        example = {
            "prompt": "test prompt",
            "segments": ["segment 1"],
            "code_lines": [[1, 2]],
        }
        assert segmentation_service._is_valid_example(example)

    def test_missing_field(self, segmentation_service):
        """Example missing required field should be invalid."""
        example = {"prompt": "test prompt", "segments": ["segment 1"]}
        assert not segmentation_service._is_valid_example(example)

    def test_empty_field(self, segmentation_service):
        """Example with empty required field should be invalid."""
        example = {"prompt": "", "segments": ["segment 1"], "code_lines": [[1]]}
        assert not segmentation_service._is_valid_example(example)


# NOTE: TestThresholdPrioritization class was removed as part of threshold consolidation.
# Threshold now only comes from segmentation_threshold DB field (no JSON fallback).
