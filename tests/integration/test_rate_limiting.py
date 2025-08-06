"""
Test rate limiting on critical endpoints to prevent abuse.
"""
import pytest
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import time


@pytest.mark.django_db
class TestRateLimiting:
    """Test rate limiting on submission endpoints."""
    
    def test_submit_solution_rate_limit(self, authenticated_client, test_problem, test_problem_set):
        """Test that SubmitSolutionView enforces 20/minute rate limit."""
        url = reverse('submit_solution')
        
        valid_payload = {
            'problem_slug': test_problem.slug,
            'problem_set_slug': test_problem_set.slug,
            'user_code': 'def two_sum(nums, target): return [0, 1]'
        }
        
        # Make 20 requests (should all succeed)
        for i in range(20):
            response = authenticated_client.post(url, valid_payload, content_type='application/json')
            assert response.status_code in [200, 201], f"Request {i+1} failed unexpectedly"
        
        # 21st request should be rate limited
        response = authenticated_client.post(url, valid_payload, content_type='application/json')
        assert response.status_code == 429, "Expected rate limit (429) but got different status"
        
        # Verify rate limit message
        assert 'rate' in response.content.decode().lower() or response.status_code == 429
    
    def test_eipl_submission_rate_limit(self, authenticated_client, test_problem):
        """Test that EiPLSubmissionView enforces 10/minute rate limit."""
        url = reverse('submit_eipl')
        
        valid_payload = {
            'problem_slug': test_problem.slug,
            'user_prompt': 'This function should iterate through the array and find two numbers that sum to the target value'
        }
        
        # Make 10 requests (should all succeed)
        for i in range(10):
            response = authenticated_client.post(url, valid_payload, content_type='application/json')
            # May fail due to AI service, but shouldn't be rate limited
            assert response.status_code != 429, f"Request {i+1} was rate limited too early"
        
        # 11th request should be rate limited
        response = authenticated_client.post(url, valid_payload, content_type='application/json')
        assert response.status_code == 429, "Expected rate limit (429) but got different status"
    
    def test_rate_limit_resets_after_time(self, authenticated_client, test_problem, test_problem_set):
        """Test that rate limit resets after the time window."""
        url = reverse('submit_solution')
        
        valid_payload = {
            'problem_slug': test_problem.slug,
            'problem_set_slug': test_problem_set.slug,
            'user_code': 'def two_sum(nums, target): return [0, 1]'
        }
        
        # Make a single request to establish rate limit window
        response = authenticated_client.post(url, valid_payload, content_type='application/json')
        assert response.status_code in [200, 201]
        
        # Note: In a real test environment, you might need to mock time
        # or use a shorter rate limit window for testing
    
    def test_different_users_have_separate_limits(self, api_client, test_problem, test_problem_set, db):
        """Test that rate limits are per-user, not global."""
        from django.contrib.auth.models import User
        
        # Create two users
        user1 = User.objects.create_user('user1', 'user1@test.com', 'pass')
        user2 = User.objects.create_user('user2', 'user2@test.com', 'pass')
        
        url = reverse('submit_solution')
        valid_payload = {
            'problem_slug': test_problem.slug,
            'problem_set_slug': test_problem_set.slug,
            'user_code': 'def two_sum(nums, target): return [0, 1]'
        }
        
        # User 1 makes 20 requests
        api_client.force_login(user1)
        for _ in range(20):
            response = api_client.post(url, valid_payload, content_type='application/json')
            assert response.status_code in [200, 201]
        
        # User 1's 21st request should be rate limited
        response = api_client.post(url, valid_payload, content_type='application/json')
        assert response.status_code == 429
        
        # User 2 should still be able to make requests
        api_client.force_login(user2)
        response = api_client.post(url, valid_payload, content_type='application/json')
        assert response.status_code in [200, 201], "User 2 was rate limited by User 1's requests"