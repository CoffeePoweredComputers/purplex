"""
Integration tests for complete workflows including submission, 
execution, scoring, progress tracking, and hint availability.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework import status

from tests.factories import (
    ProblemFactory, ProblemSetFactory, CourseFactory,
    UserFactory, CourseEnrollmentFactory, UserProgressFactory,
    HintFactory
)
from tests.mocks import MockCodeExecutionService, MockAsyncAIService
from tests.helpers import (
    SubmissionAssertions, ProgressAssertions, HintAssertions,
    TestDataHelpers
)
from purplex.problems_app.models import UserProgress, ProblemHint
from purplex.submissions.models import Submission


@pytest.mark.django_db
class TestCompleteSubmissionFlow(TransactionTestCase):
    """Test complete submission flow from input to progress update."""
    
    def setUp(self):
        self.user = UserFactory.create()
        self.problem = ProblemFactory.create(
            slug='two-sum',
            function_name='two_sum'
        )
        self.problem_set = ProblemSetFactory.create(problems=[self.problem])
        self.course = CourseFactory.create(problem_sets=[self.problem_set])
        
        # Enroll user
        CourseEnrollmentFactory.create(user=self.user, course=self.course)
        
        # Create hints
        HintFactory.create_all_types(self.problem, min_attempts=3)
        
        self.client.force_login(self.user)
        
    @patch('purplex.problems_app.services.CodeExecutionService')
    def test_first_submission_workflow(self, mock_service_class):
        """Test workflow for user's first submission."""
        # Setup mock for partial success
        mock_service = MockCodeExecutionService('partial_success')
        mock_service_class.return_value = mock_service
        
        # Verify no progress exists
        self.assertFalse(
            UserProgress.objects.filter(
                user=self.user,
                problem=self.problem
            ).exists()
        )
        
        # Submit solution
        url = reverse('submit_solution')
        payload = {
            'problem_slug': self.problem.slug,
            'problem_set_slug': self.problem_set.slug,
            'course_id': self.course.course_id,
            'user_code': '''def two_sum(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []''',
            'time_spent': 300  # 5 minutes
        }
        
        response = self.client.post(url, payload, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify response format
        data = response.json()
        SubmissionAssertions.assert_submission_response_format(data)
        
        # Verify submission created
        self.assertIsNotNone(data['submission_id'])
        submission = Submission.objects.get(submission_id=data['submission_id'])
        self.assertEqual(submission.user, self.user)
        self.assertEqual(submission.problem, self.problem)
        self.assertEqual(submission.course, self.course)
        
        # Verify progress created
        progress = UserProgress.objects.get(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            course=self.course
        )
        
        self.assertEqual(progress.attempts, 1)
        self.assertGreater(progress.best_score, 0)
        self.assertLess(progress.best_score, 100)  # Partial success
        
        # Check hints are still locked (only 1 attempt)
        hint_url = reverse('problem_hint_availability', args=[self.problem.slug])
        hint_response = self.client.get(hint_url, {
            'problem_set_slug': self.problem_set.slug,
            'course_id': self.course.course_id
        })
        
        hint_data = hint_response.json()
        self.assertEqual(hint_data['current_attempts'], 1)
        for hint in hint_data['available_hints']:
            self.assertFalse(hint['unlocked'])
            
    @patch('purplex.problems_app.services.CodeExecutionService')
    def test_multiple_submission_workflow(self, mock_service_class):
        """Test workflow with multiple submissions leading to hint unlock."""
        # Start with 2 attempts
        UserProgressFactory.create(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            course=self.course,
            attempts=2,
            best_score=70
        )
        
        # Setup mock for success
        mock_service = MockCodeExecutionService('success')
        mock_service_class.return_value = mock_service
        
        # Make third submission
        url = reverse('submit_solution')
        payload = {
            'problem_slug': self.problem.slug,
            'problem_set_slug': self.problem_set.slug,
            'course_id': self.course.course_id,
            'user_code': 'def two_sum(nums, target): return [0, 1]'
        }
        
        response = self.client.post(url, payload, content_type='application/json')
        data = response.json()
        
        # Verify perfect score
        self.assertEqual(data['score'], 100)
        self.assertEqual(data['progress']['status'], 'completed')
        self.assertEqual(data['progress']['attempts'], 3)
        
        # Check hints are now unlocked (3 attempts)
        hint_url = reverse('problem_hint_availability', args=[self.problem.slug])
        hint_response = self.client.get(hint_url, {
            'problem_set_slug': self.problem_set.slug,
            'course_id': self.course.course_id
        })
        
        hint_data = hint_response.json()
        self.assertEqual(hint_data['current_attempts'], 3)
        
        # At least some hints should be unlocked
        unlocked_hints = [h for h in hint_data['available_hints'] if h['unlocked']]
        self.assertGreater(len(unlocked_hints), 0)
        
        # Access an unlocked hint
        hint_detail_url = reverse(
            'problem_hint_detail',
            args=[self.problem.slug, 'variable_fade']
        )
        hint_detail_response = self.client.get(hint_detail_url, {
            'problem_set_slug': self.problem_set.slug,
            'course_id': self.course.course_id
        })
        
        self.assertEqual(hint_detail_response.status_code, status.HTTP_200_OK)
        HintAssertions.assert_hint_content_structure(
            hint_detail_response.json()['hint']['content'],
            'variable_fade'
        )


@pytest.mark.django_db
class TestEiPLWorkflow(TransactionTestCase):
    """Test complete EiPL submission workflow."""
    
    def setUp(self):
        self.user = UserFactory.create()
        self.problem = ProblemFactory.create(
            problem_type='eipl',
            slug='eipl-problem'
        )
        self.problem_set = ProblemSetFactory.create(problems=[self.problem])
        self.client.force_login(self.user)
        
    @patch('purplex.problems_app.async_tasks.AsyncAIService')
    def test_eipl_submission_to_progress(self, mock_ai_class):
        """Test EiPL submission from prompt to progress update."""
        # Configure mocks
        MockAsyncAIService._ai_behavior = 'success'
        mock_ai_class.generate_eipl_variations = MockAsyncAIService.generate_eipl_variations
        mock_ai_class.test_code_variations = MockAsyncAIService.test_code_variations
        
        # Submit EiPL prompt
        url = reverse('submit_eipl')
        payload = {
            'problem_slug': self.problem.slug,
            'problem_set_slug': self.problem_set.slug,
            'user_prompt': 'Iterate through the array and find two numbers that sum to the target'
        }
        
        response = self.client.post(url, payload, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify EiPL response
        data = response.json()
        SubmissionAssertions.assert_eipl_response_format(data)
        
        # Should have generated 2 variations (from mock)
        self.assertEqual(data['total_variations'], 2)
        self.assertGreater(data['passing_variations'], 0)
        
        # Verify submission created with variations
        submission = Submission.objects.get(submission_id=data['submission_id'])
        self.assertEqual(submission.user, self.user)
        self.assertEqual(submission.prompt, payload['user_prompt'])
        self.assertIn('variations', submission.test_results)
        
        # Verify progress updated
        progress = UserProgress.objects.get(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set
        )
        
        self.assertEqual(progress.attempts, 1)
        self.assertGreater(progress.best_score, 0)


@pytest.mark.django_db
class TestCrossCourseWorkflow(TransactionTestCase):
    """Test workflows across multiple courses."""
    
    def setUp(self):
        self.user = UserFactory.create()
        self.problem = ProblemFactory.create()
        self.problem_set = ProblemSetFactory.create(problems=[self.problem])
        
        # Create two courses with same problem set
        self.course1 = CourseFactory.create(
            course_id='FALL2024',
            problem_sets=[self.problem_set]
        )
        self.course2 = CourseFactory.create(
            course_id='SPRING2025',
            problem_sets=[self.problem_set]
        )
        
        # Enroll in both
        CourseEnrollmentFactory.create(user=self.user, course=self.course1)
        CourseEnrollmentFactory.create(user=self.user, course=self.course2)
        
        # Create hints
        HintFactory.create_all_types(self.problem, min_attempts=2)
        
        self.client.force_login(self.user)
        
    @patch('purplex.problems_app.services.CodeExecutionService')
    def test_independent_progress_per_course(self, mock_service_class):
        """Test that progress and hints are independent per course."""
        mock_service = MockCodeExecutionService('success')
        mock_service_class.return_value = mock_service
        
        # Submit twice in course 1
        url = reverse('submit_solution')
        for _ in range(2):
            response = self.client.post(url, {
                'problem_slug': self.problem.slug,
                'problem_set_slug': self.problem_set.slug,
                'course_id': self.course1.course_id,
                'user_code': 'def solve(): return [0, 1]'
            }, content_type='application/json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            
        # Check hints unlocked in course 1
        hint_url = reverse('problem_hint_availability', args=[self.problem.slug])
        hint_response = self.client.get(hint_url, {
            'problem_set_slug': self.problem_set.slug,
            'course_id': self.course1.course_id
        })
        
        course1_hints = hint_response.json()
        self.assertEqual(course1_hints['current_attempts'], 2)
        unlocked_in_course1 = [h for h in course1_hints['available_hints'] if h['unlocked']]
        self.assertGreater(len(unlocked_in_course1), 0)
        
        # Check hints still locked in course 2
        hint_response = self.client.get(hint_url, {
            'problem_set_slug': self.problem_set.slug,
            'course_id': self.course2.course_id
        })
        
        course2_hints = hint_response.json()
        self.assertEqual(course2_hints['current_attempts'], 0)
        unlocked_in_course2 = [h for h in course2_hints['available_hints'] if h['unlocked']]
        self.assertEqual(len(unlocked_in_course2), 0)
        
        # Verify separate progress records
        progress1 = UserProgress.objects.get(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            course=self.course1
        )
        
        # No progress in course 2 yet
        self.assertFalse(
            UserProgress.objects.filter(
                user=self.user,
                problem=self.problem,
                problem_set=self.problem_set,
                course=self.course2
            ).exists()
        )
        
        self.assertEqual(progress1.attempts, 2)
        self.assertEqual(progress1.best_score, 100)


@pytest.mark.django_db
class TestErrorScenarios(TransactionTestCase):
    """Test error handling throughout the workflow."""
    
    def setUp(self):
        self.user = UserFactory.create()
        self.problem = ProblemFactory.create()
        self.problem_set = ProblemSetFactory.create(problems=[self.problem])
        self.client.force_login(self.user)
        
    def test_invalid_problem_workflow(self):
        """Test workflow when problem doesn't exist."""
        url = reverse('submit_solution')
        response = self.client.post(url, {
            'problem_slug': 'non-existent',
            'problem_set_slug': self.problem_set.slug,
            'user_code': 'def solve(): pass'
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Verify no submission or progress created
        self.assertEqual(Submission.objects.count(), 0)
        self.assertEqual(UserProgress.objects.count(), 0)
        
    @patch('purplex.problems_app.services.CodeExecutionService')
    def test_execution_failure_workflow(self, mock_service_class):
        """Test workflow when code execution fails."""
        # Mock execution failure
        mock_service = MockCodeExecutionService('syntax_error')
        mock_service_class.return_value = mock_service
        
        url = reverse('submit_solution')
        response = self.client.post(url, {
            'problem_slug': self.problem.slug,
            'problem_set_slug': self.problem_set.slug,
            'user_code': 'invalid python code {'
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        data = response.json()
        
        # Should still have consistent error response
        SubmissionAssertions.assert_error_response_format(data, response.status_code)
        
        # Submission should be created with error
        submission = Submission.objects.get(submission_id=data['submission_id'])
        self.assertEqual(submission.score, 0)
        self.assertIn('error', submission.test_results)
        
        # Progress should show attempt
        progress = UserProgress.objects.get(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set
        )
        self.assertEqual(progress.attempts, 1)
        self.assertEqual(progress.best_score, 0)
        
    def test_unauthorized_course_access(self):
        """Test workflow when user is not enrolled in course."""
        course = CourseFactory.create(problem_sets=[self.problem_set])
        # User not enrolled
        
        url = reverse('submit_solution')
        response = self.client.post(url, {
            'problem_slug': self.problem.slug,
            'problem_set_slug': self.problem_set.slug,
            'course_id': course.course_id,
            'user_code': 'def solve(): pass'
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # No submission or progress should be created
        self.assertEqual(Submission.objects.count(), 0)
        self.assertEqual(UserProgress.objects.count(), 0)