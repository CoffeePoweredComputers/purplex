from django.test import TransactionTestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from ..models import (
    EiplProblem, ProblemHint, ProblemSet, ProblemSetMembership,
    UserProgress, Course, CourseEnrollment
)


class HintWorkflowIntegrationTests(TransactionTestCase):
    """End-to-end integration tests for the complete hint workflow"""

    def setUp(self):
        """Set up comprehensive test scenario"""
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
        
        # Create course and problem set
        self.course = Course.objects.create(
            course_id='CS101',
            name='Introduction to Programming',
            description='Basic programming concepts',
            instructor=self.admin_user
        )
        
        self.problem_set = ProblemSet.objects.create(
            slug='basics',
            title='Programming Basics',
            description='Fundamental programming problems',
            created_by=self.admin_user
        )
        
        # Create problem
        self.problem = EiplProblem.objects.create(
            slug='sum-function',
            title='Sum Function',
            function_name='add_numbers',
            function_signature='def add_numbers(a, b):',
            reference_solution='def add_numbers(a, b):\n    return a + b',
            created_by=self.admin_user
        )
        
        # Link problem to problem set
        ProblemSetMembership.objects.create(
            problem_set=self.problem_set,
            problem=self.problem,
            order=1
        )
        
        # Enroll student
        CourseEnrollment.objects.create(
            user=self.student_user,
            course=self.course,
            is_active=True
        )

    def test_complete_hint_lifecycle_admin_to_student(self):
        """Test complete workflow from admin creating hints to student using them"""
        
        # Step 1: Admin creates hint configurations
        self.client.force_authenticate(user=self.admin_user)
        
        hint_config = {
            'hints': [
                {
                    'type': 'variable_fade',
                    'is_enabled': True,
                    'min_attempts': 2,
                    'content': {
                        'mappings': [
                            {'from': 'a', 'to': 'first_number'},
                            {'from': 'b', 'to': 'second_number'}
                        ]
                    }
                },
                {
                    'type': 'subgoal_highlight',
                    'is_enabled': True,
                    'min_attempts': 3,
                    'content': {
                        'subgoals': [
                            {
                                'line_start': 1,
                                'line_end': 1,
                                'title': 'Function definition',
                                'explanation': 'Define function with two parameters'
                            },
                            {
                                'line_start': 2,
                                'line_end': 2,
                                'title': 'Return sum',
                                'explanation': 'Calculate and return the sum'
                            }
                        ]
                    }
                },
                {
                    'type': 'suggested_trace',
                    'is_enabled': False,  # Disabled
                    'min_attempts': 1,
                    'content': {
                        'suggested_call': 'add_numbers(3, 5)',
                        'explanation': 'Try this function call'
                    }
                }
            ]
        }
        
        admin_url = reverse('admin_problem_hints', kwargs={'slug': self.problem.slug})
        response = self.client.put(admin_url, hint_config, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify hints were created
        hints = ProblemHint.objects.filter(problem=self.problem)
        self.assertEqual(hints.count(), 3)
        
        enabled_hints = hints.filter(is_enabled=True)
        self.assertEqual(enabled_hints.count(), 2)
        
        # Step 2: Student attempts to access hints before meeting requirements
        self.client.force_authenticate(user=self.student_user)
        
        hint_availability_url = reverse('problem_hint_availability', kwargs={'slug': self.problem.slug})
        response = self.client.get(hint_availability_url, {
            'course_id': self.course.course_id,
            'problem_set_slug': self.problem_set.slug
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Should show 2 enabled hints, both locked
        self.assertEqual(len(data['available_hints']), 2)
        self.assertEqual(data['current_attempts'], 0)
        
        for hint in data['available_hints']:
            self.assertFalse(hint['unlocked'])
            self.assertFalse(hint['available'])
        
        # Step 3: Student makes submissions to unlock hints
        # Create user progress with attempts
        progress = UserProgress.objects.create(
            user=self.student_user,
            problem=self.problem,
            problem_set=self.problem_set,
            course=self.course,
            attempts=1
        )
        
        # Still not enough attempts for any hints
        response = self.client.get(hint_availability_url, {
            'course_id': self.course.course_id,
            'problem_set_slug': self.problem_set.slug
        })
        
        data = response.json()
        self.assertEqual(data['current_attempts'], 1)
        for hint in data['available_hints']:
            self.assertFalse(hint['unlocked'])
        
        # Make more attempts to unlock first hint (variable_fade requires 2)
        progress.attempts = 2
        progress.save()
        
        response = self.client.get(hint_availability_url, {
            'course_id': self.course.course_id,
            'problem_set_slug': self.problem_set.slug
        })
        
        data = response.json()
        self.assertEqual(data['current_attempts'], 2)
        
        # Variable fade should be unlocked, subgoal highlight still locked
        variable_fade_hint = next(h for h in data['available_hints'] if h['type'] == 'variable_fade')
        subgoal_hint = next(h for h in data['available_hints'] if h['type'] == 'subgoal_highlight')
        
        self.assertTrue(variable_fade_hint['unlocked'])
        self.assertTrue(variable_fade_hint['available'])
        self.assertFalse(subgoal_hint['unlocked'])
        self.assertFalse(subgoal_hint['available'])
        
        # Step 4: Student accesses unlocked hint content
        hint_content_url = reverse('problem_hint_detail', kwargs={
            'slug': self.problem.slug,
            'hint_type': 'variable_fade'
        })
        
        response = self.client.get(hint_content_url, {
            'course_id': self.course.course_id,
            'problem_set_slug': self.problem_set.slug
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        hint_data = response.json()
        
        self.assertEqual(hint_data['type'], 'variable_fade')
        self.assertEqual(hint_data['min_attempts'], 2)
        self.assertIn('mappings', hint_data['content'])
        self.assertEqual(len(hint_data['content']['mappings']), 2)
        
        # Step 5: Student tries to access locked hint
        hint_content_url = reverse('problem_hint_detail', kwargs={
            'slug': self.problem.slug,
            'hint_type': 'subgoal_highlight'
        })
        
        response = self.client.get(hint_content_url, {
            'course_id': self.course.course_id,
            'problem_set_slug': self.problem_set.slug
        })
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('You need 1 more attempts', response.json()['error'])
        
        # Step 6: Student makes more attempts and unlocks second hint
        progress.attempts = 4
        progress.save()
        
        response = self.client.get(hint_content_url, {
            'course_id': self.course.course_id,
            'problem_set_slug': self.problem_set.slug
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        hint_data = response.json()
        
        self.assertEqual(hint_data['type'], 'subgoal_highlight')
        self.assertIn('subgoals', hint_data['content'])
        self.assertEqual(len(hint_data['content']['subgoals']), 2)
        
        # Step 7: Verify disabled hint is not accessible
        hint_content_url = reverse('problem_hint_detail', kwargs={
            'slug': self.problem.slug,
            'hint_type': 'suggested_trace'
        })
        
        response = self.client.get(hint_content_url, {
            'course_id': self.course.course_id,
            'problem_set_slug': self.problem_set.slug
        })
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('This hint is not enabled', response.json()['error'])

    def test_hint_configuration_updates_with_existing_progress(self):
        """Test updating hint configuration when users already have progress"""
        
        # Create initial hint configuration
        ProblemHint.objects.create(
            problem=self.problem,
            hint_type='variable_fade',
            is_enabled=True,
            min_attempts=5,
            content={'mappings': []}
        )

        # Create user progress
        UserProgress.objects.create(
            user=self.student_user,
            problem=self.problem,
            problem_set=self.problem_set,
            course=self.course,
            attempts=3
        )
        
        # Student cannot access hint yet
        self.client.force_authenticate(user=self.student_user)
        
        hint_content_url = reverse('problem_hint_detail', kwargs={
            'slug': self.problem.slug,
            'hint_type': 'variable_fade'
        })
        
        response = self.client.get(hint_content_url, {
            'problem_set_slug': self.problem_set.slug
        })
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Admin updates hint to require fewer attempts
        self.client.force_authenticate(user=self.admin_user)
        
        updated_config = {
            'hints': [
                {
                    'type': 'variable_fade',
                    'is_enabled': True,
                    'min_attempts': 2,  # Reduced from 5 to 2
                    'content': {
                        'mappings': [
                            {'from': 'x', 'to': 'value'}
                        ]
                    }
                }
            ]
        }
        
        admin_url = reverse('admin_problem_hints', kwargs={'slug': self.problem.slug})
        response = self.client.put(admin_url, updated_config, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Now student should be able to access hint
        self.client.force_authenticate(user=self.student_user)
        
        response = self.client.get(hint_content_url, {
            'problem_set_slug': self.problem_set.slug
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        hint_data = response.json()
        self.assertEqual(hint_data['min_attempts'], 2)

    def test_cross_course_hint_isolation(self):
        """Test that hint progress is isolated between different courses"""
        
        # Create another course and enroll the student
        other_course = Course.objects.create(
            course_id='CS102',
            name='Advanced Programming',
            instructor=self.admin_user
        )
        
        CourseEnrollment.objects.create(
            user=self.student_user,
            course=other_course,
            is_active=True
        )
        
        # Create hint
        ProblemHint.objects.create(
            problem=self.problem,
            hint_type='variable_fade',
            is_enabled=True,
            min_attempts=2,
            content={'mappings': []}
        )
        
        # Create progress in first course
        UserProgress.objects.create(
            user=self.student_user,
            problem=self.problem,
            problem_set=self.problem_set,
            course=self.course,
            attempts=5  # More than min_attempts
        )
        
        # Create progress in second course
        UserProgress.objects.create(
            user=self.student_user,
            problem=self.problem,
            problem_set=self.problem_set,
            course=other_course,
            attempts=1  # Less than min_attempts
        )
        
        self.client.force_authenticate(user=self.student_user)
        
        # Check hint availability in first course (should be available)
        hint_availability_url = reverse('problem_hint_availability', kwargs={'slug': self.problem.slug})
        
        response = self.client.get(hint_availability_url, {
            'course_id': self.course.course_id,
            'problem_set_slug': self.problem_set.slug
        })
        
        data = response.json()
        self.assertEqual(data['current_attempts'], 5)
        self.assertTrue(data['available_hints'][0]['unlocked'])
        
        # Check hint availability in second course (should not be available)
        response = self.client.get(hint_availability_url, {
            'course_id': other_course.course_id,
            'problem_set_slug': self.problem_set.slug
        })
        
        data = response.json()
        self.assertEqual(data['current_attempts'], 1)
        self.assertFalse(data['available_hints'][0]['unlocked'])

    def test_hint_system_error_handling(self):
        """Test error handling throughout the hint system"""
        
        self.client.force_authenticate(user=self.student_user)
        
        # Test accessing hints for non-existent problem
        hint_availability_url = reverse('problem_hint_availability', kwargs={'slug': 'non-existent'})
        response = self.client.get(hint_availability_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Test accessing hints with invalid course
        hint_availability_url = reverse('problem_hint_availability', kwargs={'slug': self.problem.slug})
        response = self.client.get(hint_availability_url, {'course_id': 'INVALID123'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Test accessing hints when not enrolled in course
        other_course = Course.objects.create(
            course_id='CS999',
            name='Not Enrolled',
            instructor=self.admin_user
        )
        
        response = self.client.get(hint_availability_url, {'course_id': other_course.course_id})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Test accessing hint content for invalid hint type
        hint_content_url = reverse('problem_hint_detail', kwargs={
            'slug': self.problem.slug,
            'hint_type': 'invalid_type'
        })
        
        response = self.client.get(hint_content_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Invalid hint type', response.json()['error'])

    def test_concurrent_hint_access(self):
        """Test hint access under concurrent conditions"""
        import threading
        
        # Create hint
        ProblemHint.objects.create(
            problem=self.problem,
            hint_type='variable_fade',
            is_enabled=True,
            min_attempts=1,
            content={'mappings': []}
        )
        
        # Create progress
        UserProgress.objects.create(
            user=self.student_user,
            problem=self.problem,
            problem_set=self.problem_set,
            course=self.course,
            attempts=2
        )
        
        results = []
        
        def access_hint():
            client = APIClient()
            client.force_authenticate(user=self.student_user)
            
            hint_content_url = reverse('problem_hint_detail', kwargs={
                'slug': self.problem.slug,
                'hint_type': 'variable_fade'
            })
            
            try:
                response = client.get(hint_content_url, {
                    'problem_set_slug': self.problem_set.slug
                })
                results.append(response.status_code)
            except Exception as e:
                results.append(str(e))
        
        # Create multiple concurrent requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=access_hint)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        self.assertEqual(len(results), 5)
        for result in results:
            self.assertEqual(result, 200)

    def test_hint_data_consistency_after_multiple_updates(self):
        """Test data consistency after multiple rapid hint updates"""
        
        self.client.force_authenticate(user=self.admin_user)
        admin_url = reverse('admin_problem_hints', kwargs={'slug': self.problem.slug})
        
        # Perform multiple rapid updates
        for i in range(10):
            hint_config = {
                'hints': [
                    {
                        'type': 'variable_fade',
                        'is_enabled': True,
                        'min_attempts': i + 1,  # Different value each time
                        'content': {
                            'mappings': [
                                {'from': f'var{i}', 'to': f'variable_{i}'}
                            ]
                        }
                    }
                ]
            }
            
            response = self.client.put(admin_url, hint_config, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify final state
        hint = ProblemHint.objects.get(problem=self.problem, hint_type='variable_fade')
        self.assertEqual(hint.min_attempts, 10)  # Should have the last value
        self.assertEqual(hint.content['mappings'][0]['from'], 'var9')

    def test_hint_system_with_problem_set_without_course(self):
        """Test hint system works without course context"""
        
        # Create hint
        ProblemHint.objects.create(
            problem=self.problem,
            hint_type='variable_fade',
            is_enabled=True,
            min_attempts=2,
            content={'mappings': []}
        )
        
        # Create progress without course context
        UserProgress.objects.create(
            user=self.student_user,
            problem=self.problem,
            problem_set=self.problem_set,
            course=None,  # No course
            attempts=3
        )
        
        self.client.force_authenticate(user=self.student_user)
        
        # Access hints without course context
        hint_availability_url = reverse('problem_hint_availability', kwargs={'slug': self.problem.slug})
        response = self.client.get(hint_availability_url, {
            'problem_set_slug': self.problem_set.slug
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['current_attempts'], 3)
        self.assertTrue(data['available_hints'][0]['unlocked'])
        
        # Access hint content
        hint_content_url = reverse('problem_hint_detail', kwargs={
            'slug': self.problem.slug,
            'hint_type': 'variable_fade'
        })
        
        response = self.client.get(hint_content_url, {
            'problem_set_slug': self.problem_set.slug
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_hint_validation_edge_cases(self):
        """Test hint validation with edge case data"""
        
        self.client.force_authenticate(user=self.admin_user)
        admin_url = reverse('admin_problem_hints', kwargs={'slug': self.problem.slug})
        
        # Test with extremely large hint content
        large_mappings = []
        for i in range(1000):
            large_mappings.append({
                'from': f'variable_{i}',
                'to': f'meaningful_name_{i}'
            })
        
        hint_config = {
            'hints': [
                {
                    'type': 'variable_fade',
                    'is_enabled': True,
                    'min_attempts': 1,
                    'content': {
                        'mappings': large_mappings
                    }
                }
            ]
        }
        
        response = self.client.put(admin_url, hint_config, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify it was saved correctly
        hint = ProblemHint.objects.get(problem=self.problem, hint_type='variable_fade')
        self.assertEqual(len(hint.content['mappings']), 1000)
        
        # Test with Unicode content
        unicode_config = {
            'hints': [
                {
                    'type': 'subgoal_highlight',
                    'is_enabled': True,
                    'min_attempts': 1,
                    'content': {
                        'subgoals': [
                            {
                                'line_start': 1,
                                'line_end': 1,
                                'title': '🔧 初期化',  # Unicode and emojis
                                'explanation': 'Инициализация переменных'  # Cyrillic
                            }
                        ]
                    }
                }
            ]
        }
        
        response = self.client.put(admin_url, unicode_config, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify Unicode content is preserved
        hint = ProblemHint.objects.get(problem=self.problem, hint_type='subgoal_highlight')
        self.assertEqual(hint.content['subgoals'][0]['title'], '🔧 初期化')
        self.assertEqual(hint.content['subgoals'][0]['explanation'], 'Инициализация переменных')