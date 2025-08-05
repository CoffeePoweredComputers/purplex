"""
Tests for the hint system including availability, different hint types, 
and course context.
"""
import pytest
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from tests.factories import (
    ProblemFactory, ProblemSetFactory, CourseFactory,
    UserFactory, CourseEnrollmentFactory, UserProgressFactory,
    HintFactory
)
from tests.helpers import HintAssertions
from purplex.problems_app.models import ProblemHint, UserProgress


@pytest.mark.django_db
class TestHintAvailability(TestCase):
    """Test hint availability based on user attempts."""
    
    def setUp(self):
        self.user = UserFactory.create()
        self.problem = ProblemFactory.create()
        self.problem_set = ProblemSetFactory.create(problems=[self.problem])
        
        # Create all types of hints with default 3 attempts required
        self.hints = HintFactory.create_all_types(self.problem, min_attempts=3)
        
        self.client.force_login(self.user)
        
    def test_hints_locked_with_insufficient_attempts(self):
        """Test that hints are locked when user hasn't made enough attempts."""
        # Create progress with only 1 attempt
        UserProgressFactory.create(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            attempts=1
        )
        
        url = reverse('problem_hint_availability', args=[self.problem.slug])
        response = self.client.get(url, {
            'problem_set_slug': self.problem_set.slug
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        HintAssertions.assert_hint_availability_response(data)
        self.assertEqual(data['current_attempts'], 1)
        
        # All hints should be locked
        for hint in data['available_hints']:
            HintAssertions.assert_hint_locked(hint, current_attempts=1, required_attempts=3)
            
    def test_hints_unlocked_with_sufficient_attempts(self):
        """Test that hints unlock after minimum attempts."""
        # Create progress with 3 attempts
        UserProgressFactory.create(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            attempts=3
        )
        
        url = reverse('problem_hint_availability', args=[self.problem.slug])
        response = self.client.get(url, {
            'problem_set_slug': self.problem_set.slug
        })
        
        data = response.json()
        self.assertEqual(data['current_attempts'], 3)
        
        # Variable fade and subgoal hints should be unlocked (require 3 attempts)
        unlocked_count = 0
        for hint in data['available_hints']:
            if hint['type'] in ['variable_fade', 'subgoal_highlight']:
                HintAssertions.assert_hint_unlocked(hint)
                unlocked_count += 1
            elif hint['type'] == 'suggested_trace':
                # Trace hint requires 4 attempts
                HintAssertions.assert_hint_locked(hint, current_attempts=3, required_attempts=4)
                
        self.assertEqual(unlocked_count, 2)
        
    def test_disabled_hints_not_shown(self):
        """Test that disabled hints are not included in availability response."""
        # Disable one hint
        self.hints[0].is_enabled = False
        self.hints[0].save()
        
        url = reverse('problem_hint_availability', args=[self.problem.slug])
        response = self.client.get(url, {
            'problem_set_slug': self.problem_set.slug
        })
        
        data = response.json()
        # Should only show 2 hints (trace and subgoal)
        self.assertEqual(len(data['available_hints']), 2)
        
        # Verify disabled hint type is not present
        hint_types = [h['type'] for h in data['available_hints']]
        self.assertNotIn('variable_fade', hint_types)
        
    def test_no_progress_shows_zero_attempts(self):
        """Test that users with no progress show 0 attempts."""
        url = reverse('problem_hint_availability', args=[self.problem.slug])
        response = self.client.get(url, {
            'problem_set_slug': self.problem_set.slug
        })
        
        data = response.json()
        self.assertEqual(data['current_attempts'], 0)
        
        # All hints should be locked
        for hint in data['available_hints']:
            self.assertFalse(hint['unlocked'])
            self.assertGreater(hint['attempts_needed'], 0)


@pytest.mark.django_db
class TestHintTypes(TestCase):
    """Test different hint types and their content structure."""
    
    def setUp(self):
        self.user = UserFactory.create()
        self.problem = ProblemFactory.create()
        self.problem_set = ProblemSetFactory.create(problems=[self.problem])
        
        # Create hints and unlock them
        self.hints = HintFactory.create_all_types(self.problem, min_attempts=1)
        UserProgressFactory.create(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            attempts=5  # Enough to unlock all hints
        )
        
        self.client.force_login(self.user)
        
    def test_variable_fade_hint_content(self):
        """Test Variable Fade hint content structure."""
        url = reverse('problem_hint_detail', args=[self.problem.slug, 'variable_fade'])
        response = self.client.get(url, {
            'problem_set_slug': self.problem_set.slug
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertIn('hint', data)
        hint_content = data['hint']['content']
        
        HintAssertions.assert_hint_content_structure(hint_content, 'variable_fade')
        
        # Verify mappings
        self.assertEqual(len(hint_content['variable_mappings']), 2)
        self.assertEqual(hint_content['variable_mappings'][0]['source'], 'i')
        self.assertEqual(hint_content['variable_mappings'][0]['target'], 'index1')
        
    def test_subgoal_highlight_hint_content(self):
        """Test Subgoal Highlighting hint content structure."""
        url = reverse('problem_hint_detail', args=[self.problem.slug, 'subgoal_highlight'])
        response = self.client.get(url, {
            'problem_set_slug': self.problem_set.slug
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        hint_content = data['hint']['content']
        HintAssertions.assert_hint_content_structure(hint_content, 'subgoal_highlight')
        
        # Verify subgoals
        self.assertEqual(len(hint_content['subgoals']), 2)
        for subgoal in hint_content['subgoals']:
            self.assertGreater(len(subgoal['description']), 0)
            self.assertGreaterEqual(subgoal['end_line'], subgoal['start_line'])
            
    def test_suggested_trace_hint_content(self):
        """Test Suggested Trace hint content structure."""
        url = reverse('problem_hint_detail', args=[self.problem.slug, 'suggested_trace'])
        response = self.client.get(url, {
            'problem_set_slug': self.problem_set.slug
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        hint_content = data['hint']['content']
        HintAssertions.assert_hint_content_structure(hint_content, 'suggested_trace')
        
        # Verify trace steps
        self.assertEqual(len(hint_content['trace_steps']), 2)
        for i, step in enumerate(hint_content['trace_steps']):
            self.assertEqual(step['step'], i + 1)
            self.assertGreater(len(step['description']), 0)
            self.assertIsInstance(step['variables'], dict)
            
    def test_locked_hint_access_denied(self):
        """Test that locked hints cannot be accessed."""
        # Reset progress to 0 attempts
        progress = UserProgress.objects.get(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set
        )
        progress.attempts = 0
        progress.save()
        
        url = reverse('problem_hint_detail', args=[self.problem.slug, 'variable_fade'])
        response = self.client.get(url, {
            'problem_set_slug': self.problem_set.slug
        })
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('more attempts', data['error'])
        self.assertIn('attempts_needed', data)
        self.assertEqual(data['attempts_needed'], 1)  # Need 1 more attempt
        
    def test_invalid_hint_type(self):
        """Test accessing non-existent hint type."""
        url = reverse('problem_hint_detail', args=[self.problem.slug, 'invalid_type'])
        response = self.client.get(url, {
            'problem_set_slug': self.problem_set.slug
        })
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.json())


@pytest.mark.django_db
class TestHintCourseContext(TestCase):
    """Test hint system with course context."""
    
    def setUp(self):
        self.user = UserFactory.create()
        self.problem = ProblemFactory.create()
        self.problem_set = ProblemSetFactory.create(problems=[self.problem])
        
        # Create two courses with same problem set
        self.course1 = CourseFactory.create(
            course_id='CS101',
            problem_sets=[self.problem_set]
        )
        self.course2 = CourseFactory.create(
            course_id='CS102', 
            problem_sets=[self.problem_set]
        )
        
        # Enroll user in both courses
        CourseEnrollmentFactory.create(user=self.user, course=self.course1)
        CourseEnrollmentFactory.create(user=self.user, course=self.course2)
        
        # Create hints
        HintFactory.create_all_types(self.problem)
        
        self.client.force_login(self.user)
        
    def test_hint_availability_with_course_context(self):
        """Test that hint availability considers course-specific progress."""
        # Create different progress for each course
        UserProgressFactory.create(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            course=self.course1,
            attempts=5  # Enough for all hints
        )
        
        UserProgressFactory.create(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            course=self.course2,
            attempts=1  # Not enough for hints
        )
        
        # Check hints for course 1 (should be unlocked)
        url = reverse('problem_hint_availability', args=[self.problem.slug])
        response = self.client.get(url, {
            'problem_set_slug': self.problem_set.slug,
            'course_id': self.course1.course_id
        })
        
        data = response.json()
        self.assertEqual(data['current_attempts'], 5)
        
        # At least some hints should be unlocked
        unlocked_hints = [h for h in data['available_hints'] if h['unlocked']]
        self.assertGreater(len(unlocked_hints), 0)
        
        # Check hints for course 2 (should be locked)
        response = self.client.get(url, {
            'problem_set_slug': self.problem_set.slug,
            'course_id': self.course2.course_id
        })
        
        data = response.json()
        self.assertEqual(data['current_attempts'], 1)
        
        # All hints should be locked
        locked_hints = [h for h in data['available_hints'] if not h['unlocked']]
        self.assertEqual(len(locked_hints), len(data['available_hints']))
        
    def test_hint_access_requires_course_enrollment(self):
        """Test that hint access requires enrollment in the specified course."""
        # Create a third course user is not enrolled in
        course3 = CourseFactory.create(
            course_id='CS103',
            problem_sets=[self.problem_set]
        )
        
        url = reverse('problem_hint_availability', args=[self.problem.slug])
        response = self.client.get(url, {
            'problem_set_slug': self.problem_set.slug,
            'course_id': course3.course_id
        })
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('not enrolled', response.json()['error'])
        
    def test_hint_without_course_context(self):
        """Test that hints work without course context."""
        # Create progress without course
        UserProgressFactory.create(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            course=None,
            attempts=3
        )
        
        url = reverse('problem_hint_availability', args=[self.problem.slug])
        response = self.client.get(url, {
            'problem_set_slug': self.problem_set.slug
            # No course_id parameter
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['current_attempts'], 3)


@pytest.mark.django_db  
class TestHintUsageTracking(TestCase):
    """Test tracking of hint usage (future feature placeholder)."""
    
    def setUp(self):
        self.user = UserFactory.create()
        self.problem = ProblemFactory.create()
        self.problem_set = ProblemSetFactory.create(problems=[self.problem])
        HintFactory.create_all_types(self.problem, min_attempts=1)
        
        # Unlock hints
        UserProgressFactory.create(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            attempts=5
        )
        
        self.client.force_login(self.user)
        
    def test_hint_usage_tracking_placeholder(self):
        """Test that hint usage tracking fields are present (currently empty)."""
        url = reverse('problem_hint_availability', args=[self.problem.slug])
        response = self.client.get(url, {
            'problem_set_slug': self.problem_set.slug
        })
        
        data = response.json()
        
        # hints_used should be present but empty (not yet implemented)
        self.assertIn('hints_used', data)
        self.assertEqual(data['hints_used'], [])
        
        # TODO: When hint usage tracking is implemented, test:
        # - Recording when a hint is viewed
        # - Preventing repeated recording of same hint
        # - Tracking usage per course context
        # - Analytics on hint effectiveness