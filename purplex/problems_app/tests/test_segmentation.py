"""
Test suite for the segmentation service with verbatim validation.
"""

import unittest

from purplex.problems_app.services.segmentation_service import SegmentationService


class TestSegmentationService(unittest.TestCase):
    """Test cases for SegmentationService with verbatim validation"""

    def setUp(self):
        """Set up test fixtures"""
        self.service = SegmentationService()
        self.reference_code = """def calculate_sum(a, b):
    result = a + b
    return result"""

    def test_validate_segment_is_verbatim(self):
        """Test that verbatim validation correctly identifies exact substrings"""
        user_prompt = "This function adds two numbers together and returns their sum"

        # Test exact substring - should pass
        self.assertTrue(
            self.service._validate_segment_is_verbatim(
                "adds two numbers together", user_prompt
            )
        )

        # Test with different punctuation - should fail
        self.assertFalse(
            self.service._validate_segment_is_verbatim(
                "adds two numbers together.", user_prompt  # Extra period
            )
        )

        # Test paraphrased text - should fail
        self.assertFalse(
            self.service._validate_segment_is_verbatim(
                "combines two values", user_prompt  # Paraphrased
            )
        )

        # Test exact match with spaces
        self.assertTrue(
            self.service._validate_segment_is_verbatim("returns their sum", user_prompt)
        )

    def test_parse_segments_pure_segmentation(self):
        """Test that _parse_segments returns segments with one-to-one mapping"""
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

        result = self.service._parse_segments(
            ai_response, self.reference_code, user_prompt
        )

        # Should have all non-overlapping segments
        self.assertTrue(result["success"])
        self.assertEqual(len(result["segments"]), 3)  # 3 non-overlapping segments

        # Check that all segments are included
        segment_texts = [seg["text"] for seg in result["segments"]]
        self.assertIn("takes two parameters", segment_texts)
        self.assertIn("return", segment_texts)
        self.assertIn(
            "combines the values", segment_texts
        )  # Non-verbatim also included

    def test_function_definition_segments_not_filtered(self):
        """Test that function definition segments are NOT filtered (pure segmentation)"""
        user_prompt = "The function takes two numbers and returns their sum"

        ai_response = """
        {
            "segments": [
                {"id": 1, "text": "function takes two numbers", "code_lines": [1]},
                {"id": 2, "text": "returns their sum", "code_lines": [2]}
            ]
        }
        """

        result = self.service._parse_segments(
            ai_response, self.reference_code, user_prompt
        )

        # Both segments should be included even though first contains "function takes"
        self.assertTrue(result["success"])
        self.assertEqual(len(result["segments"]), 2)

        segment_texts = [seg["text"] for seg in result["segments"]]
        self.assertIn("function takes two numbers", segment_texts)  # Not filtered!
        self.assertIn("returns their sum", segment_texts)

    def test_create_segmentation_prompt_includes_verbatim_rules(self):
        """Test that the prompt includes strict one-to-one mapping rules"""
        prompt = self.service._create_segmentation_prompt(self.reference_code)

        # Check for critical one-to-one mapping rules (current format)
        self.assertIn("CRITICAL ONE-TO-ONE MAPPING RULES", prompt)
        self.assertIn("EXACTLY ONE distinct code section", prompt)
        self.assertIn("no overlapping", prompt.lower())
        self.assertIn("ONE-TO-ONE MAPPING VALIDATION", prompt)

        # Check that function definition filtering instruction is REMOVED
        self.assertNotIn(
            "Remove any segments that just describe function definition", prompt
        )

    def test_segmentation_with_custom_examples(self):
        """Test segmentation prompt with custom examples"""
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

        prompt = self.service._create_segmentation_prompt(
            self.reference_code, custom_examples
        )

        # Check that instructor examples are included (current format uses plain text headings)
        self.assertIn("SEGMENTATION EXAMPLES", prompt)
        self.assertIn("RELATIONAL", prompt)
        self.assertIn("MULTI-STRUCTURAL", prompt)
        self.assertIn(custom_examples["relational"]["prompt"], prompt)
        self.assertIn(custom_examples["multi_structural"]["prompt"], prompt)


if __name__ == "__main__":
    unittest.main()
