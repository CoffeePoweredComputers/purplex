"""
Comprehensive tests for the submission pipeline including validation, 
authorization, execution, and scoring.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.urls import reverse
from django.test import TestCase
from rest_framework import status

from tests.factories import (
    ProblemFactory, ProblemSetFactory, CourseFactory, 
    UserFactory, CourseEnrollmentFactory, UserProgressFactory
)
from tests.mocks import MockCodeExecutionService, MockAsyncAIService
from tests.helpers import (
    SubmissionAssertions, TestDataHelpers, ProgressAssertions
)


@pytest.mark.django_db
class TestSubmissionInputValidation(TestCase):
    """Test input validation for submission endpoints."""
    
    def setUp(self):
        self.user = UserFactory.create()
        self.problem = ProblemFactory.create()
        self.problem_set = ProblemSetFactory.create(problems=[self.problem])
        self.client.force_login(self.user)
        
    def test_code_size_validation(self):
        """Test that code submissions are limited to 50KB."""
        url = reverse('submit_solution')
        
        # Test code at limit (50000 chars)
        valid_payload = TestDataHelpers.create_valid_code_submission()
        valid_payload['user_code'] = 'x' * 50000
        response = self.client.post(url, valid_payload, content_type='application/json')
        # Should succeed (assuming mock execution)
        self.assertNotEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test code over limit
        invalid_payload = TestDataHelpers.create_valid_code_submission()
        invalid_payload['user_code'] = 'x' * 50001
        response = self.client.post(url, invalid_payload, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('exceed 50000 characters', response.json()['error'])
        
    def test_prompt_length_validation(self):
        """Test EiPL prompt length validation (10-2000 chars)."""
        url = reverse('submit_eipl')
        
        # Test prompt too short
        short_payload = {
            'problem_slug': self.problem.slug,
            'user_prompt': 'short'  # < 10 chars
        }
        response = self.client.post(url, short_payload, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('at least 10 characters', response.json()['error'])
        
        # Test prompt too long
        long_payload = {
            'problem_slug': self.problem.slug,
            'user_prompt': 'x' * 2001  # > 2000 chars
        }
        response = self.client.post(url, long_payload, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('exceed 2000 characters', response.json()['error'])
        
        # Test valid prompt
        valid_payload = TestDataHelpers.create_valid_eipl_submission()
        valid_payload['problem_slug'] = self.problem.slug
        with patch('purplex.problems_app.async_tasks.AsyncAIService') as mock_ai:
            mock_ai.generate_eipl_variations.return_value = {
                'success': True,
                'variations': ['def solve(): pass']
            }
            response = self.client.post(url, valid_payload, content_type='application/json')
            # Should not be validation error
            if response.status_code == status.HTTP_400_BAD_REQUEST:
                self.assertNotIn('characters', response.json().get('error', ''))
                
    def test_script_injection_prevention(self):
        """Test that script injection attempts are blocked."""
        url = reverse('submit_eipl')
        
        malicious_prompts = [
            '<script>alert("XSS")</script>',
            '<?php echo "hack"; ?>',
            '<% response.write("asp") %>',
            '<jsp:include page="hack.jsp" />'
        ]
        
        for prompt in malicious_prompts:
            payload = {
                'problem_slug': self.problem.slug,
                'user_prompt': f'Valid text {prompt} more text'  # Ensure > 10 chars
            }
            response = self.client.post(url, payload, content_type='application/json')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('Invalid characters', response.json()['error'])
            
    def test_missing_required_fields(self):
        """Test that missing required fields are properly handled."""
        # Test submit solution
        url = reverse('submit_solution')
        
        # Missing user_code
        response = self.client.post(url, {
            'problem_slug': self.problem.slug,
            'problem_set_slug': self.problem_set.slug
        }, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('required', response.json()['error'])
        
        # Missing problem_slug
        response = self.client.post(url, {
            'user_code': 'def solve(): pass',
            'problem_set_slug': self.problem_set.slug
        }, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('required', response.json()['error'])


@pytest.mark.django_db
class TestSubmissionAuthorization(TestCase):
    """Test authorization and access control for submissions."""
    
    def setUp(self):
        self.user = UserFactory.create()
        self.other_user = UserFactory.create(username='otheruser')
        self.problem = ProblemFactory.create()
        self.problem_set = ProblemSetFactory.create(problems=[self.problem])
        self.course = CourseFactory.create(problem_sets=[self.problem_set])
        self.client.force_login(self.user)
        
    def test_course_enrollment_required(self):
        """Test that users must be enrolled in course to submit."""
        url = reverse('submit_solution')
        payload = TestDataHelpers.create_valid_code_submission()
        payload.update({
            'problem_slug': self.problem.slug,
            'problem_set_slug': self.problem_set.slug,
            'course_id': self.course.course_id
        })
        
        # Not enrolled - should fail
        response = self.client.post(url, payload, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('not enrolled', response.json()['error'])
        
        # Enroll user
        CourseEnrollmentFactory.create(user=self.user, course=self.course)
        
        # Now should pass authorization (may fail at execution)
        with patch('purplex.problems_app.services.CodeExecutionService') as mock_service:
            mock_service.return_value.test_solution.return_value = {
                'passed': 1, 'total': 1, 'results': []
            }
            response = self.client.post(url, payload, content_type='application/json')
            self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            
    def test_problem_set_membership_validation(self):
        """Test that problem must belong to the specified problem set."""
        # Create another problem not in the set
        other_problem = ProblemFactory.create(slug='other-problem')
        
        url = reverse('submit_solution')
        payload = TestDataHelpers.create_valid_code_submission()
        payload.update({
            'problem_slug': other_problem.slug,  # Problem not in set
            'problem_set_slug': self.problem_set.slug
        })
        
        response = self.client.post(url, payload, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('does not belong', response.json()['error'])
        
    def test_course_problem_set_validation(self):
        """Test that problem set must belong to the course."""
        # Create another problem set not in course
        other_set = ProblemSetFactory.create(slug='other-set')
        other_problem = ProblemFactory.create(slug='other-prob')
        other_set.problems.add(other_problem)
        
        # Enroll user in course
        CourseEnrollmentFactory.create(user=self.user, course=self.course)
        
        url = reverse('submit_solution')
        payload = TestDataHelpers.create_valid_code_submission()
        payload.update({
            'problem_slug': other_problem.slug,
            'problem_set_slug': other_set.slug,
            'course_id': self.course.course_id
        })
        
        response = self.client.post(url, payload, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Problem set does not belong to this course', response.json()['error'])


@pytest.mark.django_db
class TestCodeExecution(TestCase):
    """Test code execution and error handling."""
    
    def setUp(self):
        self.user = UserFactory.create()
        self.problem = ProblemFactory.create()
        self.problem_set = ProblemSetFactory.create(problems=[self.problem])
        self.client.force_login(self.user)
        
    @patch('purplex.problems_app.services.CodeExecutionService')
    def test_successful_execution(self, mock_service_class):
        """Test successful code execution flow."""
        # Setup mock
        mock_service = MockCodeExecutionService('success')
        mock_service_class.return_value = mock_service
        
        url = reverse('submit_solution')
        payload = TestDataHelpers.create_valid_code_submission()
        payload.update({
            'problem_slug': self.problem.slug,
            'problem_set_slug': self.problem_set.slug
        })
        
        response = self.client.post(url, payload, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify response format
        SubmissionAssertions.assert_submission_response_format(response.json())
        
        # Verify all tests passed
        data = response.json()
        self.assertEqual(data['passed'], data['total'])
        self.assertEqual(data['score'], 100)
        
    @patch('purplex.problems_app.services.CodeExecutionService')
    def test_partial_success(self, mock_service_class):
        """Test handling of partial test success."""
        # Setup mock for partial success
        mock_service = MockCodeExecutionService('partial_success')
        mock_service_class.return_value = mock_service
        
        url = reverse('submit_solution')
        payload = TestDataHelpers.create_valid_code_submission()
        payload.update({
            'problem_slug': self.problem.slug,
            'problem_set_slug': self.problem_set.slug
        })
        
        response = self.client.post(url, payload, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        # Should have some passed, some failed
        self.assertGreater(data['passed'], 0)
        self.assertLess(data['passed'], data['total'])
        self.assertLess(data['score'], 100)
        self.assertGreater(data['score'], 0)
        
    @patch('purplex.problems_app.services.CodeExecutionService')
    def test_execution_timeout(self, mock_service_class):
        """Test handling of code execution timeout."""
        # Setup mock for timeout
        mock_service = MockCodeExecutionService('timeout')
        mock_service_class.return_value = mock_service
        
        url = reverse('submit_solution')
        payload = TestDataHelpers.create_valid_code_submission()
        payload.update({
            'problem_slug': self.problem.slug,
            'problem_set_slug': self.problem_set.slug
        })
        
        response = self.client.post(url, payload, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        data = response.json()
        SubmissionAssertions.assert_error_response_format(data, response.status_code)
        self.assertEqual(data['score'], 0)
        self.assertEqual(data['passed'], 0)
        
    @patch('purplex.problems_app.services.CodeExecutionService')
    def test_syntax_error_handling(self, mock_service_class):
        """Test handling of syntax errors in submitted code."""
        # Setup mock for syntax error
        mock_service = MockCodeExecutionService('syntax_error')
        mock_service_class.return_value = mock_service
        
        url = reverse('submit_solution')
        payload = TestDataHelpers.create_valid_code_submission()
        payload.update({
            'problem_slug': self.problem.slug,
            'problem_set_slug': self.problem_set.slug
        })
        
        response = self.client.post(url, payload, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        data = response.json()
        self.assertEqual(data['score'], 0)
        self.assertEqual(data['passed'], 0)


@pytest.mark.django_db
class TestScoringAndResults(TestCase):
    """Test scoring calculation and result formatting."""
    
    def setUp(self):
        self.user = UserFactory.create()
        # Create problem with 2 visible and 1 hidden test case
        self.problem = ProblemFactory.create(
            num_test_cases=3,
            num_hidden=1
        )
        self.problem_set = ProblemSetFactory.create(problems=[self.problem])
        self.client.force_login(self.user)
        
    @patch('purplex.problems_app.services.CodeExecutionService')
    def test_score_calculation(self, mock_service_class):
        """Test that score is calculated as (passed/total) * 100."""
        mock_service = MockCodeExecutionService('partial_success')
        mock_service_class.return_value = mock_service
        
        url = reverse('submit_solution')
        payload = TestDataHelpers.create_valid_code_submission()
        payload.update({
            'problem_slug': self.problem.slug,
            'problem_set_slug': self.problem_set.slug
        })
        
        response = self.client.post(url, payload, content_type='application/json')
        data = response.json()
        
        # Score should be (passed/total) * 100
        expected_score = int((data['passed'] / data['total']) * 100)
        self.assertEqual(data['score'], expected_score)
        
    @patch('purplex.problems_app.services.CodeExecutionService')
    def test_hidden_test_case_filtering(self, mock_service_class):
        """Test that hidden test results are not returned to students."""
        # Mock all tests passing
        mock_service = MockCodeExecutionService('success')
        mock_service_class.return_value = mock_service
        
        url = reverse('submit_solution')
        payload = TestDataHelpers.create_valid_code_submission()
        payload.update({
            'problem_slug': self.problem.slug,
            'problem_set_slug': self.problem_set.slug
        })
        
        response = self.client.post(url, payload, content_type='application/json')
        data = response.json()
        
        # Should run all 3 tests
        self.assertEqual(data['total'], 3)
        self.assertEqual(data['passed'], 3)
        
        # But only return 2 visible results
        self.assertEqual(len(data['results']), 2)  # Only visible test results
        
    def test_progress_update_on_submission(self):
        """Test that UserProgress is updated after submission."""
        # Verify no progress exists initially
        from purplex.problems_app.models import UserProgress
        self.assertFalse(
            UserProgress.objects.filter(
                user=self.user,
                problem=self.problem,
                problem_set=self.problem_set
            ).exists()
        )
        
        with patch('purplex.problems_app.services.CodeExecutionService') as mock_service_class:
            mock_service = MockCodeExecutionService('success')
            mock_service_class.return_value = mock_service
            
            url = reverse('submit_solution')
            payload = TestDataHelpers.create_valid_code_submission()
            payload.update({
                'problem_slug': self.problem.slug,
                'problem_set_slug': self.problem_set.slug
            })
            
            response = self.client.post(url, payload, content_type='application/json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            
            # Verify progress was created
            progress = UserProgress.objects.get(
                user=self.user,
                problem=self.problem,
                problem_set=self.problem_set
            )
            
            self.assertEqual(progress.attempts, 1)
            self.assertEqual(progress.best_score, 100)
            self.assertEqual(progress.status, 'completed')
            
            # Verify progress is returned in response
            data = response.json()
            self.assertIn('progress', data)
            self.assertEqual(data['progress']['best_score'], 100)
            self.assertEqual(data['progress']['attempts'], 1)
            self.assertTrue(data['progress']['is_completed'])


@pytest.mark.django_db
class TestEiPLSubmission(TestCase):
    """Test EiPL (Explain in Plain Language) submission flow."""
    
    def setUp(self):
        self.user = UserFactory.create()
        self.problem = ProblemFactory.create(problem_type='eipl')
        self.problem_set = ProblemSetFactory.create(problems=[self.problem])
        self.client.force_login(self.user)
        
    @patch('purplex.problems_app.async_tasks.AsyncAIService')
    def test_successful_eipl_submission(self, mock_ai_class):
        """Test successful EiPL submission with AI generation."""
        # Configure AI mock
        MockAsyncAIService._ai_behavior = 'success'
        
        url = reverse('submit_eipl')
        payload = TestDataHelpers.create_valid_eipl_submission()
        payload.update({
            'problem_slug': self.problem.slug,
            'problem_set_slug': self.problem_set.slug
        })
        
        # Mock the AI service methods
        mock_ai_class.generate_eipl_variations = MockAsyncAIService.generate_eipl_variations
        mock_ai_class.test_code_variations = MockAsyncAIService.test_code_variations
        
        response = self.client.post(url, payload, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify EiPL response format
        data = response.json()
        SubmissionAssertions.assert_eipl_response_format(data)
        
        # Should have 2 variations from mock
        self.assertEqual(data['total_variations'], 2)
        self.assertGreater(data['passing_variations'], 0)
        
    @patch('purplex.problems_app.async_tasks.AsyncAIService')
    def test_ai_timeout_handling(self, mock_ai_class):
        """Test handling of AI service timeouts."""
        # Configure AI mock for timeout
        MockAsyncAIService._ai_behavior = 'timeout'
        
        url = reverse('submit_eipl')
        payload = TestDataHelpers.create_valid_eipl_submission()
        payload.update({
            'problem_slug': self.problem.slug,
            'problem_set_slug': self.problem_set.slug
        })
        
        mock_ai_class.generate_eipl_variations = MockAsyncAIService.generate_eipl_variations
        
        response = self.client.post(url, payload, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        data = response.json()
        self.assertIn('timeout', data['error'].lower())
        self.assertEqual(data['submission_id'], None)
        self.assertEqual(data['score'], 0)