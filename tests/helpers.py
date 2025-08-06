"""
Test helpers and assertion utilities for consistent testing.
"""
from django.test import TestCase


class SubmissionAssertions:
    """Assertion helpers for submission responses."""
    
    @staticmethod
    def assert_submission_response_format(response_data):
        """Verify submission response has correct structure."""
        # Required fields for all submission responses
        required_fields = ['submission_id', 'score', 'passed', 'total', 'results']
        
        for field in required_fields:
            assert field in response_data, f"Missing required field: {field}"
            
        # Verify types
        assert isinstance(response_data.get('score'), (int, float))
        assert isinstance(response_data.get('passed'), int)
        assert isinstance(response_data.get('total'), int)
        assert isinstance(response_data.get('results'), list)
        
        # Verify score is between 0 and 100
        assert 0 <= response_data['score'] <= 100, "Score must be between 0 and 100"
        
        # Verify passed <= total
        assert response_data['passed'] <= response_data['total'], "Passed count cannot exceed total"
        
    @staticmethod
    def assert_error_response_format(response_data, status_code):
        """Verify error response has correct structure."""
        assert 'error' in response_data, "Error response must contain 'error' field"
        assert isinstance(response_data['error'], str)
        assert len(response_data['error']) > 0, "Error message cannot be empty"
        
        # For submission endpoints, even errors should have consistent structure
        if status_code >= 400:
            if 'submission_id' in response_data:
                assert response_data['submission_id'] is None
            if 'score' in response_data:
                assert response_data['score'] == 0
                
    @staticmethod
    def assert_eipl_response_format(response_data):
        """Verify EiPL submission response has correct structure."""
        # All fields from regular submission
        SubmissionAssertions.assert_submission_response_format(response_data)
        
        # Additional EiPL fields
        eipl_fields = ['variations', 'passing_variations', 'total_variations']
        
        for field in eipl_fields:
            assert field in response_data, f"Missing EiPL field: {field}"
            
        assert isinstance(response_data.get('variations'), list)
        assert isinstance(response_data.get('passing_variations'), int)
        assert isinstance(response_data.get('total_variations'), int)
        
        # Verify counts
        assert response_data['total_variations'] == len(response_data['variations'])
        assert response_data['passing_variations'] <= response_data['total_variations']


class ProgressAssertions:
    """Assertion helpers for progress tracking."""
    
    @staticmethod
    def assert_progress_updated(progress, expected_values):
        """Verify progress was updated with expected values."""
        for field, expected in expected_values.items():
            actual = getattr(progress, field)
            assert actual == expected, f"Progress.{field} = {actual}, expected {expected}"
            
    @staticmethod
    def assert_progress_incremented(old_progress, new_progress):
        """Verify attempts were incremented."""
        assert new_progress.attempts == old_progress.attempts + 1
        
    @staticmethod
    def assert_best_score_updated(progress, new_score):
        """Verify best score was updated if higher."""
        assert progress.best_score >= new_score, "Best score should not decrease"
        
    @staticmethod
    def assert_progress_isolated_by_course(progress1, progress2):
        """Verify progress records are isolated by course."""
        # Same user, problem, and problem_set
        assert progress1.user == progress2.user
        assert progress1.problem == progress2.problem
        assert progress1.problem_set == progress2.problem_set
        
        # Different courses
        assert progress1.course != progress2.course
        
        # Independent values
        assert progress1.attempts != progress2.attempts or progress1.attempts == 0
        assert progress1.best_score != progress2.best_score or progress1.best_score == 0


class HintAssertions:
    """Assertion helpers for hint system."""
    
    @staticmethod
    def assert_hint_availability_response(response_data):
        """Verify hint availability response structure."""
        required_fields = ['available_hints', 'hints_used', 'current_attempts']
        
        for field in required_fields:
            assert field in response_data, f"Missing required field: {field}"
            
        assert isinstance(response_data['available_hints'], list)
        assert isinstance(response_data['hints_used'], list)
        assert isinstance(response_data['current_attempts'], int)
        
        # Check each hint structure
        for hint in response_data['available_hints']:
            hint_fields = ['type', 'title', 'description', 'unlocked', 'available', 'attempts_needed']
            for field in hint_fields:
                assert field in hint, f"Hint missing field: {field}"
                
    @staticmethod
    def assert_hint_locked(hint_data, current_attempts, required_attempts):
        """Verify hint is properly locked."""
        assert not hint_data['unlocked']
        assert not hint_data['available']
        assert hint_data['attempts_needed'] == required_attempts - current_attempts
        
    @staticmethod
    def assert_hint_unlocked(hint_data):
        """Verify hint is properly unlocked."""
        assert hint_data['unlocked']
        assert hint_data['available']
        assert hint_data['attempts_needed'] == 0
        
    @staticmethod
    def assert_hint_content_structure(hint_content, hint_type):
        """Verify hint content has correct structure for its type."""
        if hint_type == 'variable_fade':
            assert 'variable_mappings' in hint_content
            assert isinstance(hint_content['variable_mappings'], list)
            for mapping in hint_content['variable_mappings']:
                assert 'source' in mapping
                assert 'target' in mapping
                
        elif hint_type == 'subgoal_highlight':
            assert 'subgoals' in hint_content
            assert isinstance(hint_content['subgoals'], list)
            for subgoal in hint_content['subgoals']:
                assert 'id' in subgoal
                assert 'description' in subgoal
                assert 'start_line' in subgoal
                assert 'end_line' in subgoal
                
        elif hint_type == 'suggested_trace':
            assert 'trace_steps' in hint_content
            assert isinstance(hint_content['trace_steps'], list)
            for step in hint_content['trace_steps']:
                assert 'step' in step
                assert 'description' in step
                assert 'variables' in step


class TestDataHelpers:
    """Helpers for creating consistent test data."""
    
    @staticmethod
    def create_valid_code_submission():
        """Create a valid code submission payload."""
        return {
            'problem_slug': 'test-problem',
            'problem_set_slug': 'test-set',
            'user_code': '''def solve(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []'''
        }
        
    @staticmethod
    def create_valid_eipl_submission():
        """Create a valid EiPL submission payload."""
        return {
            'problem_slug': 'test-problem',
            'problem_set_slug': 'test-set',
            'user_prompt': 'Iterate through the array and find two numbers that sum to the target value'
        }
        
    @staticmethod
    def create_invalid_submissions():
        """Create various invalid submission payloads for testing."""
        return [
            # Missing required fields
            {'problem_slug': 'test-problem'},  # Missing user_code/prompt
            {'user_code': 'print("hello")'},   # Missing problem_slug
            
            # Invalid field values
            {'problem_slug': 'test-problem', 'user_code': 'x' * 50001},  # Code too long
            {'problem_slug': 'test-problem', 'user_prompt': 'short'},    # Prompt too short
            {'problem_slug': 'test-problem', 'user_prompt': 'x' * 2001}, # Prompt too long
            
            # Injection attempts
            {'problem_slug': 'test-problem', 'user_prompt': '<script>alert("XSS")</script>'},
            {'problem_slug': 'test-problem', 'user_prompt': '<?php echo "hack"; ?>'},
        ]