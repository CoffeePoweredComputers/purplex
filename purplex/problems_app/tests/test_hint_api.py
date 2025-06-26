import json
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from ..models import Problem, ProblemHint, ProblemSet, UserProgress, Course, CourseEnrollment


class HintAPITests(TestCase):
    """Test suite for hint-related API endpoints"""

    def setUp(self):
        """Set up test data for hint API tests"""
        self.client = APIClient()
        
        # Create users
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123'
        )
        self.admin_user.is_staff = True
        self.admin_user.is_superuser = True
        self.admin_user.save()
        
        self.student_user = User.objects.create_user(
            username='student',
            email='student@example.com',
            password='testpass123'
        )
        
        # Create test problem
        self.problem = Problem.objects.create(
            slug='test-problem',
            title='Test Problem',
            description='Test problem description',
            function_name='test_function',
            function_signature='def test_function():',
            reference_solution='def test_function():\n    return True',
            created_by=self.admin_user
        )
        
        # Create test problem set
        self.problem_set = ProblemSet.objects.create(
            slug='test-set',
            title='Test Problem Set',
            description='Test problem set',
            created_by=self.admin_user
        )
        
        # Create test course
        self.course = Course.objects.create(
            course_id='TEST101',
            name='Test Course',
            description='Test course description',
            instructor=self.admin_user
        )
        
        # Enroll student in course
        CourseEnrollment.objects.create(
            user=self.student_user,
            course=self.course
        )

    def test_get_hint_availability_no_hints_configured(self):
        """Test getting hint availability when no hints are configured"""
        self.client.force_authenticate(user=self.student_user)
        
        url = reverse('problem_hint_availability', kwargs={'slug': self.problem.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertEqual(data['available_hints'], [])
        self.assertEqual(data['hints_used'], [])
        self.assertEqual(data['current_attempts'], 0)

    def test_get_hint_availability_with_hints_configured(self):
        """Test getting hint availability with configured hints"""
        # Create hints
        ProblemHint.objects.create(
            problem=self.problem,
            hint_type='variable_fade',
            is_enabled=True,
            min_attempts=3,
            content={'mappings': [{'from': 'x', 'to': 'count'}]}
        )
        
        ProblemHint.objects.create(
            problem=self.problem,
            hint_type='subgoal_highlight',
            is_enabled=True,
            min_attempts=2,
            content={'subgoals': []}
        )
        
        # Create disabled hint (should not appear)
        ProblemHint.objects.create(
            problem=self.problem,
            hint_type='suggested_trace',
            is_enabled=False,
            min_attempts=1,
            content={'suggested_call': 'test()'}
        )
        
        self.client.force_authenticate(user=self.student_user)
        
        url = reverse('problem_hint_availability', kwargs={'slug': self.problem.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Should only show enabled hints
        self.assertEqual(len(data['available_hints']), 2)
        
        hint_types = [hint['type'] for hint in data['available_hints']]
        self.assertIn('variable_fade', hint_types)
        self.assertIn('subgoal_highlight', hint_types)
        self.assertNotIn('suggested_trace', hint_types)
        
        # All hints should be locked (0 attempts)
        for hint in data['available_hints']:
            self.assertFalse(hint['unlocked'])
            self.assertFalse(hint['available'])

    def test_get_hint_availability_with_progress(self):
        """Test hint availability with user progress"""
        # Create hint
        ProblemHint.objects.create(
            problem=self.problem,
            hint_type='variable_fade',
            is_enabled=True,
            min_attempts=3,
            content={'mappings': []}
        )
        
        # Create user progress with attempts
        UserProgress.objects.create(
            user=self.student_user,
            problem=self.problem,
            problem_set=self.problem_set,
            attempts=5  # More than min_attempts
        )
        
        self.client.force_authenticate(user=self.student_user)
        
        url = reverse('problem_hint_availability', kwargs={'slug': self.problem.slug})
        response = self.client.get(url, {'problem_set_slug': self.problem_set.slug})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Hint should be unlocked
        self.assertEqual(len(data['available_hints']), 1)
        hint = data['available_hints'][0]
        self.assertTrue(hint['unlocked'])
        self.assertTrue(hint['available'])
        self.assertEqual(hint['attempts_needed'], 0)
        self.assertEqual(data['current_attempts'], 5)

    def test_get_hint_content_success(self):
        """Test getting hint content successfully"""
        hint = ProblemHint.objects.create(
            problem=self.problem,
            hint_type='variable_fade',
            is_enabled=True,
            min_attempts=1,
            content={
                'mappings': [
                    {'from': 'x', 'to': 'count'},
                    {'from': 'y', 'to': 'total'}
                ]
            }
        )
        
        # Create progress to unlock hint
        UserProgress.objects.create(
            user=self.student_user,
            problem=self.problem,
            problem_set=self.problem_set,
            attempts=2
        )
        
        self.client.force_authenticate(user=self.student_user)
        
        url = reverse('problem_hint_detail', kwargs={
            'slug': self.problem.slug,
            'hint_type': 'variable_fade'
        })
        response = self.client.get(url, {'problem_set_slug': self.problem_set.slug})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertEqual(data['type'], 'variable_fade')
        self.assertEqual(data['content'], hint.content)
        self.assertEqual(data['min_attempts'], 1)

    def test_get_hint_content_not_unlocked(self):
        """Test getting hint content when not unlocked"""
        ProblemHint.objects.create(
            problem=self.problem,
            hint_type='variable_fade',
            is_enabled=True,
            min_attempts=5,
            content={'mappings': []}
        )
        
        # Create progress with insufficient attempts
        UserProgress.objects.create(
            user=self.student_user,
            problem=self.problem,
            problem_set=self.problem_set,
            attempts=2  # Less than min_attempts
        )
        
        self.client.force_authenticate(user=self.student_user)
        
        url = reverse('problem_hint_detail', kwargs={
            'slug': self.problem.slug,
            'hint_type': 'variable_fade'
        })
        response = self.client.get(url, {'problem_set_slug': self.problem_set.slug})
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        data = response.json()
        self.assertIn('You need 3 more attempts', data['error'])

    def test_get_hint_content_hint_not_found(self):
        """Test getting hint content for non-existent hint"""
        self.client.force_authenticate(user=self.student_user)
        
        url = reverse('problem_hint_detail', kwargs={
            'slug': self.problem.slug,
            'hint_type': 'variable_fade'
        })
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.json()
        self.assertIn('Hint not found', data['error'])

    def test_get_hint_content_disabled_hint(self):
        """Test getting content for disabled hint"""
        ProblemHint.objects.create(
            problem=self.problem,
            hint_type='variable_fade',
            is_enabled=False,  # Disabled
            min_attempts=1,
            content={'mappings': []}
        )
        
        UserProgress.objects.create(
            user=self.student_user,
            problem=self.problem,
            problem_set=self.problem_set,
            attempts=5
        )
        
        self.client.force_authenticate(user=self.student_user)
        
        url = reverse('problem_hint_detail', kwargs={
            'slug': self.problem.slug,
            'hint_type': 'variable_fade'
        })
        response = self.client.get(url, {'problem_set_slug': self.problem_set.slug})
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        data = response.json()
        self.assertIn('This hint is not enabled', data['error'])

    def test_admin_get_problem_hints(self):
        """Test admin endpoint to get all hint configurations"""
        # Create hints
        ProblemHint.objects.create(
            problem=self.problem,
            hint_type='variable_fade',
            is_enabled=True,
            min_attempts=3,
            content={'mappings': []}
        )
        
        ProblemHint.objects.create(
            problem=self.problem,
            hint_type='subgoal_highlight',
            is_enabled=False,
            min_attempts=2,
            content={'subgoals': []}
        )
        
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('admin_problem_hints', kwargs={'slug': self.problem.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertEqual(data['problem_slug'], self.problem.slug)
        self.assertEqual(len(data['hints']), 3)  # Should include default configs for missing types
        
        # Check that all hint types are present
        hint_types = [hint['type'] for hint in data['hints']]
        self.assertIn('variable_fade', hint_types)
        self.assertIn('subgoal_highlight', hint_types)
        self.assertIn('suggested_trace', hint_types)

    def test_admin_update_hints_success(self):
        """Test admin endpoint to update hint configurations"""
        hints_data = {
            'hints': [
                {
                    'type': 'variable_fade',
                    'is_enabled': True,
                    'min_attempts': 3,
                    'content': {
                        'mappings': [
                            {'from': 'x', 'to': 'count'},
                            {'from': 'y', 'to': 'total'}
                        ]
                    }
                },
                {
                    'type': 'subgoal_highlight',
                    'is_enabled': True,
                    'min_attempts': 2,
                    'content': {
                        'subgoals': [
                            {
                                'line_start': 1,
                                'line_end': 3,
                                'title': 'Initialize',
                                'explanation': 'Set up variables'
                            }
                        ]
                    }
                },
                {
                    'type': 'suggested_trace',
                    'is_enabled': False,
                    'min_attempts': 1,
                    'content': {
                        'suggested_call': 'test_function()',
                        'explanation': 'Try this call'
                    }
                }
            ]
        }
        
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('admin_problem_hints', kwargs={'slug': self.problem.slug})
        response = self.client.put(url, hints_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertEqual(data['problem_slug'], self.problem.slug)
        self.assertEqual(len(data['hints']), 3)
        
        # Verify hints were created/updated
        self.assertEqual(ProblemHint.objects.filter(problem=self.problem).count(), 3)
        
        variable_fade_hint = ProblemHint.objects.get(
            problem=self.problem,
            hint_type='variable_fade'
        )
        self.assertTrue(variable_fade_hint.is_enabled)
        self.assertEqual(len(variable_fade_hint.content['mappings']), 2)

    def test_admin_update_hints_invalid_content(self):
        """Test admin update with invalid hint content"""
        hints_data = {
            'hints': [
                {
                    'type': 'variable_fade',
                    'is_enabled': True,
                    'min_attempts': 3,
                    'content': {
                        'mappings': 'invalid_not_a_list'  # Should be a list
                    }
                }
            ]
        }
        
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('admin_problem_hints', kwargs={'slug': self.problem.slug})
        response = self.client.put(url, hints_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn('error', data)

    def test_admin_update_hints_invalid_type(self):
        """Test admin update with invalid hint type"""
        hints_data = {
            'hints': [
                {
                    'type': 'invalid_hint_type',
                    'is_enabled': True,
                    'min_attempts': 3,
                    'content': {}
                }
            ]
        }
        
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('admin_problem_hints', kwargs={'slug': self.problem.slug})
        response = self.client.put(url, hints_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn('Invalid hint type', data['error'])

    def test_admin_update_hints_missing_type(self):
        """Test admin update with missing hint type"""
        hints_data = {
            'hints': [
                {
                    # Missing 'type' field
                    'is_enabled': True,
                    'min_attempts': 3,
                    'content': {}
                }
            ]
        }
        
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('admin_problem_hints', kwargs={'slug': self.problem.slug})
        response = self.client.put(url, hints_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn('Each hint must have a type field', data['error'])

    def test_hint_access_without_authentication(self):
        """Test hint endpoints require authentication"""
        url = reverse('problem_hint_availability', kwargs={'slug': self.problem.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_hints_require_admin_permission(self):
        """Test admin hint endpoints require admin permission"""
        self.client.force_authenticate(user=self.student_user)
        
        url = reverse('admin_problem_hints', kwargs={'slug': self.problem.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_hint_with_course_context(self):
        """Test hint availability with course context"""
        ProblemHint.objects.create(
            problem=self.problem,
            hint_type='variable_fade',
            is_enabled=True,
            min_attempts=2,
            content={'mappings': []}
        )
        
        # Create progress with course context
        UserProgress.objects.create(
            user=self.student_user,
            problem=self.problem,
            problem_set=self.problem_set,
            course=self.course,
            attempts=3
        )
        
        self.client.force_authenticate(user=self.student_user)
        
        url = reverse('problem_hint_availability', kwargs={'slug': self.problem.slug})
        response = self.client.get(url, {
            'course_id': self.course.course_id,
            'problem_set_slug': self.problem_set.slug
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertEqual(data['current_attempts'], 3)
        self.assertTrue(data['available_hints'][0]['unlocked'])

    def test_hint_with_invalid_course(self):
        """Test hint availability with invalid course ID"""
        self.client.force_authenticate(user=self.student_user)
        
        url = reverse('problem_hint_availability', kwargs={'slug': self.problem.slug})
        response = self.client.get(url, {'course_id': 'INVALID123'})
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.json()
        self.assertIn('Course not found', data['error'])

    def test_hint_access_not_enrolled_course(self):
        """Test hint access when not enrolled in course"""
        other_course = Course.objects.create(
            course_id='OTHER101',
            name='Other Course',
            instructor=self.admin_user
        )
        
        self.client.force_authenticate(user=self.student_user)
        
        url = reverse('problem_hint_availability', kwargs={'slug': self.problem.slug})
        response = self.client.get(url, {'course_id': other_course.course_id})
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        data = response.json()
        self.assertIn('You are not enrolled in this course', data['error'])

    def test_concurrent_hint_updates(self):
        """Test concurrent hint updates don't cause data corruption"""
        from django.db import transaction
        import threading
        
        results = []
        
        def update_hints():
            try:
                with transaction.atomic():
                    self.client.force_authenticate(user=self.admin_user)
                    
                    hints_data = {
                        'hints': [
                            {
                                'type': 'variable_fade',
                                'is_enabled': True,
                                'min_attempts': 3,
                                'content': {'mappings': []}
                            }
                        ]
                    }
                    
                    url = reverse('admin_problem_hints', kwargs={'slug': self.problem.slug})
                    response = self.client.put(url, hints_data, format='json')
                    results.append(response.status_code)
            except Exception as e:
                results.append(str(e))
        
        # Run concurrent updates
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=update_hints)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # At least one should succeed
        self.assertIn(200, results)
        
        # Verify final state is consistent
        hint_count = ProblemHint.objects.filter(problem=self.problem).count()
        self.assertEqual(hint_count, 1)  # Only one hint should exist

    def test_large_hint_content(self):
        """Test handling of large hint content"""
        # Create a large subgoal list
        large_subgoals = []
        for i in range(1000):
            large_subgoals.append({
                'line_start': i * 2 + 1,
                'line_end': i * 2 + 2,
                'title': f'Step {i + 1}',
                'explanation': f'This is a very long explanation for step {i + 1}. ' * 10
            })
        
        hints_data = {
            'hints': [
                {
                    'type': 'subgoal_highlight',
                    'is_enabled': True,
                    'min_attempts': 1,
                    'content': {'subgoals': large_subgoals}
                }
            ]
        }
        
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('admin_problem_hints', kwargs={'slug': self.problem.slug})
        response = self.client.put(url, hints_data, format='json')
        
        # Should handle large content gracefully
        self.assertEqual(response.status_code, status.HTTP_200_OK)