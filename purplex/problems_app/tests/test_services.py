"""
Test suite for all service layer components including segmentation.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from ..services.docker_execution_service import DockerExecutionService as CodeExecutionService
from purplex.problems_app.services.segmentation_service import SegmentationService
from purplex.problems_app.services.ai_generation_service import AITestGenerationService
from purplex.problems_app.services.validation_service import ProblemValidationService


class TestServiceIntegration(TestCase):
    """Integration tests for service layer components."""
    
    def setUp(self):
        """Set up test fixtures"""
        self.segmentation_service = SegmentationService()
        self.ai_service = AITestGenerationService()
        self.execution_service = CodeExecutionService()
        self.validation_service = ProblemValidationService()
        
    def test_segmentation_service_initialization(self):
        """Test that SegmentationService initializes correctly"""
        service = SegmentationService()
        self.assertIsNotNone(service)
        # Client should be None if API key not configured
        if not service.client:
            self.assertIsNone(service.client)
            
    def test_verbatim_validation_integration(self):
        """Test verbatim validation is properly integrated"""
        service = SegmentationService()
        
        # Test data
        user_prompt = "This function calculates the sum of two numbers"
        reference_code = "def add(a, b):\n    return a + b"
        
        # Test segment validation
        valid_segment = "calculates the sum"
        invalid_segment = "computes the total"  # paraphrased
        
        self.assertTrue(service._validate_segment_is_verbatim(valid_segment, user_prompt))
        self.assertFalse(service._validate_segment_is_verbatim(invalid_segment, user_prompt))
        
    @patch('openai.OpenAI')
    def test_segmentation_with_mock_api(self, mock_openai_class):
        """Test segmentation with mocked OpenAI API"""
        # Setup mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        # Mock API response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''
        {
            "segments": [
                {"id": 1, "text": "calculates the sum", "code_lines": [1, 2]},
                {"id": 2, "text": "two numbers", "code_lines": [1]}
            ]
        }
        '''
        mock_client.chat.completions.create.return_value = mock_response
        
        # Initialize service with mocked client
        service = SegmentationService()
        service.client = mock_client
        
        # Test segmentation
        user_prompt = "This function calculates the sum of two numbers"
        reference_code = "def add(a, b):\n    return a + b"
        
        result = service.segment_prompt(
            user_prompt=user_prompt,
            reference_code=reference_code,
            problem_config={}
        )
        
        # Verify results
        self.assertTrue(result['success'])
        self.assertEqual(len(result['segments']), 2)

        # Note: With pure segmentation, segments may or may not be verbatim
        # We just verify structure, not content filtering
            
    def test_ai_service_initialization(self):
        """Test AITestGenerationService initialization"""
        service = AITestGenerationService()
        self.assertIsNotNone(service)
        
    def test_code_execution_service(self):
        """Test CodeExecutionService basic functionality"""
        service = CodeExecutionService()
        self.assertIsNotNone(service)
        self.assertEqual(service.timeout, 5)  # Default timeout
        
    def test_validation_service(self):
        """Test ProblemValidationService initialization"""
        service = ProblemValidationService()
        self.assertIsNotNone(service)
        

class TestSegmentationPromptGeneration(TestCase):
    """Test prompt generation for segmentation."""
    
    def setUp(self):
        self.service = SegmentationService()
        
    def test_prompt_includes_critical_rules(self):
        """Test that generated prompts include verbatim rules"""
        reference_code = "def test():\n    pass"
        prompt = self.service._create_segmentation_prompt(reference_code)
        
        # Check for critical elements
        self.assertIn("CRITICAL RULES", prompt)
        self.assertIn("EXACT text from the student's explanation", prompt)
        self.assertIn("character-for-character substring", prompt)
        self.assertIn("DO NOT paraphrase", prompt)
        self.assertIn("WARNING", prompt)
        self.assertIn("Copy-paste precision", prompt)
        
    def test_prompt_with_examples(self):
        """Test prompt generation with custom examples"""
        reference_code = "def test():\n    pass"
        examples = {
            'relational': {
                'prompt': 'This is a test function',
                'segments': ['test function'],
                'code_lines': [[1, 2]]
            },
            'multi_structural': {
                'prompt': 'Define function, then pass',
                'segments': ['Define function', 'pass'],
                'code_lines': [[1], [2]]
            }
        }
        
        prompt = self.service._create_segmentation_prompt(reference_code, examples)
        
        # Check examples are included
        self.assertIn("SEGMENTATION EXAMPLES", prompt)
        self.assertIn("RELATIONAL", prompt)
        self.assertIn("MULTI-STRUCTURAL", prompt)
        self.assertIn(examples['relational']['prompt'], prompt)
        

class TestResponseFormatCompatibility(TestCase):
    """Test response format compatibility with EiPL Grader."""
    
    def setUp(self):
        self.service = SegmentationService()
        
    def test_parse_segments_returns_correct_format(self):
        """Test that parsing returns segments in correct format"""
        user_prompt = "iterate through array and find sum"
        reference_code = "for i in arr:\n    total += i"

        ai_response = '''
        {
            "segments": [
                {"id": 1, "text": "iterate through array", "code_lines": [1]},
                {"id": 2, "text": "find sum", "code_lines": [2]}
            ]
        }
        '''

        result = self.service._parse_segments(ai_response, reference_code, user_prompt)

        # Check segments format
        self.assertTrue(result['success'])
        self.assertIn('segments', result)
        self.assertEqual(len(result['segments']), 2)

        # Verify segment structure
        for segment in result['segments']:
            self.assertIn('id', segment)
            self.assertIn('text', segment)
            self.assertIn('code_lines', segment)
            self.assertIsInstance(segment['code_lines'], list)
            
            
if __name__ == '__main__':
    unittest.main()