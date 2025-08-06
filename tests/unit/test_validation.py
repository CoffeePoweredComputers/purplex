"""
Test input validation for security-critical endpoints.
"""
import pytest
from django.urls import reverse
from django.core.exceptions import ValidationError
from purplex.problems_app.validation_service import ProblemValidationService


@pytest.mark.django_db
class TestInputValidation:
    """Test input validation across the application."""
    
    def test_eipl_prompt_length_validation(self, authenticated_client, test_problem):
        """Test EiPL prompt length limits."""
        url = reverse('submit_eipl')
        
        # Test too short prompt (< 10 chars)
        short_payload = {
            'problem_slug': test_problem.slug,
            'user_prompt': 'short'
        }
        response = authenticated_client.post(url, short_payload, content_type='application/json')
        assert response.status_code == 400
        assert 'at least 10 characters' in response.json()['error']
        
        # Test too long prompt (> 2000 chars)
        long_payload = {
            'problem_slug': test_problem.slug,
            'user_prompt': 'x' * 2001
        }
        response = authenticated_client.post(url, long_payload, content_type='application/json')
        assert response.status_code == 400
        assert 'exceed 2000 characters' in response.json()['error']
        
        # Test valid prompt length
        valid_payload = {
            'problem_slug': test_problem.slug,
            'user_prompt': 'This is a valid prompt that describes the solution approach'
        }
        response = authenticated_client.post(url, valid_payload, content_type='application/json')
        # May fail due to AI service, but shouldn't be validation error
        assert response.status_code != 400 or 'characters' not in response.json().get('error', '')
    
    def test_eipl_prompt_content_validation(self, authenticated_client, test_problem):
        """Test EiPL prompt content validation to prevent injection."""
        url = reverse('submit_eipl')
        
        # Test script injection attempts
        malicious_prompts = [
            '<script>alert("XSS")</script>',
            '<?php echo "hack"; ?>',
            '<% response.write("asp") %>',
            '<jsp:include page="hack.jsp" />'
        ]
        
        for prompt in malicious_prompts:
            payload = {
                'problem_slug': test_problem.slug,
                'user_prompt': f'Valid text {prompt} more valid text'
            }
            response = authenticated_client.post(url, payload, content_type='application/json')
            assert response.status_code == 400
            assert 'Invalid characters' in response.json()['error']
    
    def test_code_submission_size_limit(self, authenticated_client, test_problem, test_problem_set):
        """Test code submission size limits."""
        url = reverse('submit_solution')
        
        # Test code too large (> 50KB)
        large_code = 'x' * 50001
        payload = {
            'problem_slug': test_problem.slug,
            'problem_set_slug': test_problem_set.slug,
            'user_code': large_code
        }
        response = authenticated_client.post(url, payload, content_type='application/json')
        assert response.status_code == 400
        assert 'exceed 50000 characters' in response.json()['error']
        
        # Test valid code size
        valid_code = 'def two_sum(nums, target): return [0, 1]'
        payload['user_code'] = valid_code
        response = authenticated_client.post(url, payload, content_type='application/json')
        assert response.status_code in [200, 201]
    
    def test_problem_validation_service_function_name(self):
        """Test ProblemValidationService validates function names."""
        service = ProblemValidationService()
        
        # Valid function names
        valid_names = ['two_sum', 'calculate_total', 'is_valid', 'parse123']
        for name in valid_names:
            is_valid, message = service.validate_function_name(name)
            assert is_valid is True, f"Expected {name} to be valid but got: {message}"
        
        # Invalid function names
        invalid_names = ['2sum', 'calculate-total', 'class', 'def', 'import os']
        for name in invalid_names:
            is_valid, message = service.validate_function_name(name)
            assert is_valid is False, f"Expected {name} to be invalid"
    
    def test_problem_validation_service_reserved_words(self):
        """Test that reserved Python keywords are rejected."""
        service = ProblemValidationService()
        
        reserved_words = ['class', 'def', 'import', 'return', 'if', 'else', 'for', 'while']
        for word in reserved_words:
            is_valid, message = service.validate_function_name(word)
            assert is_valid is False, f"Expected reserved word '{word}' to be invalid"
    
    def test_missing_required_fields(self, authenticated_client, test_problem):
        """Test that missing required fields are properly validated."""
        url = reverse('submit_solution')
        
        # Missing user_code
        payload = {
            'problem_slug': test_problem.slug,
            'problem_set_slug': 'some-set'
        }
        response = authenticated_client.post(url, payload, content_type='application/json')
        assert response.status_code == 400
        assert 'required' in response.json()['error']
        
        # Missing problem_slug
        payload = {
            'user_code': 'def two_sum(nums, target): return [0, 1]',
            'problem_set_slug': 'some-set'
        }
        response = authenticated_client.post(url, payload, content_type='application/json')
        assert response.status_code == 400
        assert 'required' in response.json()['error']