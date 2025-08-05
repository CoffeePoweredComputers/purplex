"""
Test data factories for creating consistent test objects.
"""
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from purplex.problems_app.models import (
    Problem, ProblemSet, TestCase, Course, CourseEnrollment, 
    UserProgress, ProblemHint
)
from purplex.submissions_app.models import PromptSubmission


class ProblemFactory:
    """Factory for creating test problems."""
    
    @staticmethod
    def create(
        title="Test Problem",
        slug="test-problem",
        problem_type="function_redefinition",
        difficulty="easy",
        function_name="solve",
        with_test_cases=True,
        num_test_cases=3,
        num_hidden=1
    ):
        """Create a problem with optional test cases."""
        problem = Problem.objects.create(
            title=title,
            slug=slug,
            problem_type=problem_type,
            description="Test problem description",
            difficulty=difficulty,
            function_name=function_name,
            function_signature=f"def {function_name}(nums: List[int], target: int) -> List[int]:",
            reference_solution="""def solve(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []""",
            is_active=True
        )
        
        if with_test_cases:
            # Create visible test cases
            for i in range(num_test_cases - num_hidden):
                TestCase.objects.create(
                    problem=problem,
                    inputs={"nums": [2, 7, 11, 15], "target": 9},
                    expected_output=[0, 1],
                    description=f"Test case {i + 1}",
                    is_hidden=False,
                    order=i + 1
                )
            
            # Create hidden test cases
            for i in range(num_hidden):
                TestCase.objects.create(
                    problem=problem,
                    inputs={"nums": [3, 2, 4], "target": 6},
                    expected_output=[1, 2],
                    description=f"Hidden test case {i + 1}",
                    is_hidden=True,
                    order=num_test_cases - num_hidden + i + 1
                )
        
        return problem


class ProblemSetFactory:
    """Factory for creating test problem sets."""
    
    @staticmethod
    def create(title="Test Problem Set", slug="test-set", problems=None):
        """Create a problem set with optional problems."""
        problem_set = ProblemSet.objects.create(
            title=title,
            slug=slug,
            description="Test problem set"
        )
        
        if problems:
            problem_set.problems.set(problems)
            
        return problem_set


class CourseFactory:
    """Factory for creating test courses."""
    
    @staticmethod
    def create(
        course_id="TEST101",
        name="Test Course",
        instructor=None,
        problem_sets=None
    ):
        """Create a course with optional instructor and problem sets."""
        if not instructor:
            instructor = UserFactory.create(username="instructor")
            
        course = Course.objects.create(
            course_id=course_id,
            name=name,
            description="Test course description",
            instructor=instructor,
            is_active=True
        )
        
        if problem_sets:
            course.problem_sets.set(problem_sets)
            
        return course


class UserFactory:
    """Factory for creating test users."""
    
    @staticmethod
    def create(username="testuser", email=None, is_admin=False):
        """Create a test user."""
        if not email:
            email = f"{username}@example.com"
            
        user = User.objects.create_user(
            username=username,
            email=email,
            password="testpass123"
        )
        
        if is_admin:
            user.is_staff = True
            user.is_superuser = True
            user.save()
            
        return user


class UserProgressFactory:
    """Factory for creating user progress records."""
    
    @staticmethod
    def create(
        user,
        problem,
        problem_set,
        course=None,
        attempts=0,
        best_score=0,
        status='not_started'
    ):
        """Create or update user progress."""
        progress, created = UserProgress.objects.update_or_create(
            user=user,
            problem=problem,
            problem_set=problem_set,
            course=course,
            defaults={
                'attempts': attempts,
                'best_score': best_score,
                'status': status,
                'total_time_spent': timedelta(minutes=attempts * 5)
            }
        )
        return progress


class SubmissionFactory:
    """Factory for creating test submissions."""
    
    @staticmethod
    def create(
        user,
        problem,
        problem_set,
        course=None,
        score=100,
        prompt="Test submission",
        test_results=None
    ):
        """Create a test submission."""
        if not test_results:
            test_results = {
                'passed': 3,
                'total': 3,
                'results': [
                    {'test_number': 1, 'pass': True},
                    {'test_number': 2, 'pass': True},
                    {'test_number': 3, 'pass': True}
                ]
            }
            
        submission = PromptSubmission.objects.create(
            user=user,
            problem=problem,
            problem_set=problem_set,
            course=course,
            score=score,
            prompt=prompt,
            test_results=test_results,
            time_spent=timedelta(minutes=5)
        )
        
        return submission


class HintFactory:
    """Factory for creating problem hints."""
    
    @staticmethod
    def create_all_types(problem, min_attempts=3):
        """Create all three types of hints for a problem."""
        hints = []
        
        # Variable Fade hint
        hints.append(ProblemHint.objects.create(
            problem=problem,
            hint_type='variable_fade',
            content={
                'variable_mappings': [
                    {'source': 'i', 'target': 'index1'},
                    {'source': 'j', 'target': 'index2'}
                ],
                'description': 'Variable names have been changed to be more descriptive'
            },
            min_attempts=min_attempts,
            is_enabled=True
        ))
        
        # Subgoal Highlighting hint
        hints.append(ProblemHint.objects.create(
            problem=problem,
            hint_type='subgoal_highlight',
            content={
                'subgoals': [
                    {
                        'id': 'sg1',
                        'description': 'Initialize the outer loop',
                        'start_line': 1,
                        'end_line': 1
                    },
                    {
                        'id': 'sg2',
                        'description': 'Check if sum equals target',
                        'start_line': 3,
                        'end_line': 4
                    }
                ]
            },
            min_attempts=min_attempts,
            is_enabled=True
        ))
        
        # Suggested Trace hint
        hints.append(ProblemHint.objects.create(
            problem=problem,
            hint_type='suggested_trace',
            content={
                'trace_steps': [
                    {
                        'step': 1,
                        'description': 'Start with i=0',
                        'variables': {'i': 0, 'nums': '[2, 7, 11, 15]', 'target': 9}
                    },
                    {
                        'step': 2,
                        'description': 'Inner loop with j=1',
                        'variables': {'i': 0, 'j': 1, 'nums[i]': 2, 'nums[j]': 7}
                    }
                ],
                'explanation': 'This trace shows how the algorithm finds the solution'
            },
            min_attempts=min_attempts + 1,  # Trace hints require more attempts
            is_enabled=True
        ))
        
        return hints


class CourseEnrollmentFactory:
    """Factory for enrolling users in courses."""
    
    @staticmethod
    def create(user, course, role='student'):
        """Enroll a user in a course."""
        enrollment = CourseEnrollment.objects.create(
            user=user,
            course=course,
            role=role,
            is_active=True
        )
        return enrollment