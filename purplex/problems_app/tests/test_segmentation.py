"""
Test suite for the segmentation service with verbatim validation.
"""
import unittest
from unittest.mock import Mock, patch
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
                "adds two numbers together",
                user_prompt
            )
        )
        
        # Test with different punctuation - should fail
        self.assertFalse(
            self.service._validate_segment_is_verbatim(
                "adds two numbers together.",  # Extra period
                user_prompt
            )
        )
        
        # Test paraphrased text - should fail
        self.assertFalse(
            self.service._validate_segment_is_verbatim(
                "combines two values",  # Paraphrased
                user_prompt
            )
        )
        
        # Test exact match with spaces
        self.assertTrue(
            self.service._validate_segment_is_verbatim(
                "returns their sum",
                user_prompt
            )
        )
        
    def test_parse_segments_pure_segmentation(self):
        """Test that _parse_segments returns all segments (pure segmentation)"""
        user_prompt = "The function takes two parameters and adds them"
        
        # Mock AI response with both verbatim and non-verbatim segments
        ai_response = '''
        {
            "segments": [
                {"id": 1, "text": "takes two parameters", "code_lines": [1]},
                {"id": 2, "text": "combines the values", "code_lines": [2]},
                {"id": 3, "text": "adds them", "code_lines": [2]}
            ]
        }
        '''
        
        result = self.service._parse_segments(ai_response, self.reference_code, user_prompt)
        
        # Should have ALL segments (pure segmentation - no filtering)
        self.assertTrue(result['success'])
        self.assertEqual(len(result['segments']), 3)  # All 3 segments returned
        
        # Check that all segments are included
        segment_texts = [seg['text'] for seg in result['segments']]
        self.assertIn('takes two parameters', segment_texts)
        self.assertIn('adds them', segment_texts)
        self.assertIn('combines the values', segment_texts)  # Non-verbatim also included
        
        # Verify EiPL Grader format (groups) is also present
        self.assertIn('groups', result)
        self.assertEqual(len(result['groups']), 3)  # All 3 groups
        
        # Check groups format
        for group in result['groups']:
            self.assertIn('explanation_portion', group)
            self.assertIn('code', group)
        
    def test_function_definition_segments_not_filtered(self):
        """Test that function definition segments are NOT filtered (pure segmentation)"""
        user_prompt = "The function takes two numbers and returns their sum"
        
        ai_response = '''
        {
            "segments": [
                {"id": 1, "text": "function takes two numbers", "code_lines": [1]},
                {"id": 2, "text": "returns their sum", "code_lines": [2]}
            ]
        }
        '''
        
        result = self.service._parse_segments(ai_response, self.reference_code, user_prompt)
        
        # Both segments should be included even though first contains "function takes"
        self.assertTrue(result['success'])
        self.assertEqual(len(result['segments']), 2)
        
        segment_texts = [seg['text'] for seg in result['segments']]
        self.assertIn('function takes two numbers', segment_texts)  # Not filtered!
        self.assertIn('returns their sum', segment_texts)
    
    def test_create_segmentation_prompt_includes_verbatim_rules(self):
        """Test that the prompt includes strict verbatim extraction rules"""
        prompt = self.service._create_segmentation_prompt(self.reference_code)
        
        # Check for critical rules
        self.assertIn("CRITICAL RULES", prompt)
        self.assertIn("EXACT text from the student's explanation", prompt)
        self.assertIn("character-for-character substring", prompt)
        self.assertIn("DO NOT paraphrase", prompt)
        self.assertIn("Copy text VERBATIM", prompt)
        self.assertIn("WARNING", prompt)
        
        # Check that function definition filtering instruction is REMOVED
        self.assertNotIn("Remove any segments that just describe function definition", prompt)
        
    def test_segmentation_with_custom_examples(self):
        """Test segmentation prompt with custom examples"""
        custom_examples = {
            'relational': {
                'prompt': 'This function calculates the sum of two numbers',
                'segments': ['calculates the sum of two numbers'],
                'code_lines': [[1, 2, 3]]
            },
            'multi_structural': {
                'prompt': 'First it takes parameters, then adds them, finally returns result',
                'segments': ['takes parameters', 'adds them', 'returns result'],
                'code_lines': [[1], [2], [3]]
            }
        }
        
        prompt = self.service._create_segmentation_prompt(self.reference_code, custom_examples)
        
        # Check that examples are included
        self.assertIn("SEGMENTATION EXAMPLES", prompt)
        self.assertIn("RELATIONAL", prompt)
        self.assertIn("MULTI-STRUCTURAL", prompt)
        self.assertIn(custom_examples['relational']['prompt'], prompt)
        self.assertIn(custom_examples['multi_structural']['prompt'], prompt)


if __name__ == '__main__':
    unittest.main()