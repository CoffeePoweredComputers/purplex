"""Service for managing user progress with transaction safety and caching."""

import logging
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from datetime import datetime
from django.core.cache import cache
from django.db import transaction

from ..repositories import (
    ProgressRepository, ProblemRepository, CourseRepository,
    ProblemSetMembershipRepository
)

# Import models only for type hints
if TYPE_CHECKING:
    from django.db import models
    from django.db.models import F, Q, Count, Avg
    from django.contrib.auth.models import User
    from ..models import UserProgress, UserProblemSetProgress, Problem, ProblemSet, Course
    from purplex.submissions.models import Submission

logger = logging.getLogger(__name__)


class ProgressService:
    """Service for managing user progress with proper locking and caching."""
    
    @staticmethod
    @transaction.atomic
    def update_user_progress(
        user_id: int,
        problem_id: int,
        submission: 'Submission',
        problem_set_id: Optional[int] = None,
        course_id: Optional[int] = None
    ) -> 'UserProgress':
        """
        Update user progress for a problem with row-level locking.
        
        This method uses select_for_update to prevent race conditions when multiple
        submissions are processed concurrently.
        """
        try:
            # Get or create progress using repository with locking
            progress, created = ProgressRepository.get_or_create_with_lock(
                user_id=user_id,
                problem_id=problem_id,
                problem_set_id=problem_set_id,
                course_id=course_id
            )
            
            # Update progress metrics
            progress.attempts = progress.attempts + 1
            progress.last_attempt = datetime.now()
            
            # Update score if better
            if submission.score > progress.best_score:
                progress.best_score = submission.score

            # Use CompletionEvaluator to determine the actual status
            from purplex.submissions.completion_evaluator import CompletionEvaluator
            status = CompletionEvaluator.compute_user_progress_status(progress)

            # Update progress status based on evaluator
            progress.status = status

            # Update completion fields based on status
            if status == 'completed':
                progress.is_completed = True
                progress.completion_percentage = 100
                if not progress.completed_at:
                    progress.completed_at = datetime.now()
            elif status == 'in_progress':
                progress.is_completed = False
                # Use submission score for completion percentage if not completed
                progress.completion_percentage = min(submission.score, 99)  # Cap at 99 if not fully complete
            else:
                progress.is_completed = False
                progress.completion_percentage = 0
            
            progress.save()
            
            # Invalidate relevant caches
            ProgressService._invalidate_progress_cache(user_id, problem_id, problem_set_id)
            
            # Update problem set progress if applicable
            if problem_set_id:
                ProgressService._update_problem_set_progress(
                    user_id, problem_set_id, course_id
                )
            
            logger.info(
                f"Updated progress for user {user_id} on problem {problem_id}: "
                f"attempts={progress.attempts}, best_score={progress.best_score}"
            )
            
            return progress
            
        except Exception as e:
            logger.error(f"Error updating user progress: {str(e)}")
            raise
    
    @staticmethod
    def get_user_progress(
        user_id: int,
        problem_id: int,
        problem_set_id: Optional[int] = None,
        course_id: Optional[int] = None
    ) -> Optional['UserProgress']:
        """
        Get user progress for a specific problem.
        
        Args:
            user_id: User ID
            problem_id: Problem ID
            problem_set_id: Optional problem set ID for context
            course_id: Optional course ID for context
            
        Returns:
            UserProgress instance or None
        """
        return ProgressRepository.get_by_ids(
            user_id=user_id,
            problem_id=problem_id,
            problem_set_id=problem_set_id,
            course_id=course_id
        )
    
    @staticmethod
    @transaction.atomic
    def bulk_update_progress(
        user_id: int,
        updates: List[Dict[str, Any]]
    ) -> List['UserProgress']:
        """
        Bulk update multiple progress records with transaction safety.
        
        Args:
            user_id: User ID
            updates: List of dicts with problem_id, score, status, etc.
        """
        updated_progress = []
        
        for update in updates:
            problem_id = update.get('problem_id')
            if not problem_id:
                continue
                
            progress = ProgressRepository.get_with_lock(
                user_id=user_id,
                problem_id=problem_id
            )
            
            if progress:
                for field, value in update.items():
                    if field != 'problem_id' and hasattr(progress, field):
                        setattr(progress, field, value)
                progress.save()
                updated_progress.append(progress)
        
        # Clear user's progress cache
        cache_key = f'user_progress_all:{user_id}'
        cache.delete(cache_key)
        
        return updated_progress
    
    @staticmethod
    def get_cached_progress(
        user_id: int,
        problem_id: Optional[int] = None,
        problem_set_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached progress data with fallback to database.
        
        Returns:
            Progress data dict or None if not found
        """
        # Build cache key
        if problem_id:
            cache_key = f'user_progress:{user_id}:problem:{problem_id}'
        elif problem_set_id:
            cache_key = f'user_progress:{user_id}:set:{problem_set_id}'
        else:
            cache_key = f'user_progress_all:{user_id}'
        
        # Try cache first
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data
        
        # Fetch from database
        if problem_id:
            data = ProgressRepository.get_progress_with_problem(
                user_id=user_id,
                problem_id=problem_id
            )
            
            if data:
                # Cache for 5 minutes
                cache.set(cache_key, data, 300)
                return data
                
        elif problem_set_id:
            data = ProgressRepository.get_problem_set_progress_with_relations(
                user_id=user_id,
                problem_set_id=problem_set_id
            )
            
            if data:
                # Cache for 5 minutes
                cache.set(cache_key, data, 300)
                return data
        
        return None
    
    @staticmethod
    def get_all_user_progress(user_id: int) -> List[Dict[str, Any]]:
        """
        Get all progress records for a user with caching.
        
        Args:
            user_id: User ID
            
        Returns:
            List of progress dictionaries
        """
        # Try cache first
        cache_key = f'user_progress_all:{user_id}'
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        # Fetch from database with optimized query
        progress_data = ProgressRepository.get_all_progress_with_problems(user_id)
        
        # Cache for 5 minutes
        cache.set(cache_key, progress_data, 300)
        
        return progress_data
    
    @staticmethod
    def get_problem_progress(user_id: int, problem_slug: str) -> Dict[str, Any]:
        """
        Get progress for a specific problem.
        
        Args:
            user_id: User ID
            problem_slug: Problem slug
            
        Returns:
            Progress dictionary or default values if not found
        """
        try:
            problem = ProblemRepository.get_problem_by_slug(problem_slug)
            if not problem:
                raise ValueError(f"Problem with slug {problem_slug} not found")
            
            try:
                progress = ProgressRepository.get_by_ids(user_id, problem.id) if problem else None
                return {
                    'problem_slug': problem.slug,
                    'status': progress.status,
                    'best_score': progress.best_score,
                    'attempts': progress.attempts,
                    'is_completed': progress.is_completed,
                    'completion_percentage': progress.completion_percentage,
                    'last_attempt': progress.last_attempt,
                    'completed_at': progress.completed_at,
                }
            except Exception:
                # Return default values
                return {
                    'problem_slug': problem.slug,
                    'status': 'not_started',
                    'best_score': 0,
                    'attempts': 0,
                    'is_completed': False,
                    'completion_percentage': 0,
                    'last_attempt': None,
                    'completed_at': None,
                }
        except Exception:
            raise ValueError(f"Problem with slug {problem_slug} not found")
    
    @staticmethod
    def get_or_create_problem_set_progress(
        user: 'User',
        problem_set: 'ProblemSet',
        course: Optional['Course'] = None
    ) -> 'UserProblemSetProgress':
        """
        Get or create problem set progress using repository.
        
        Args:
            user: The user
            problem_set: The problem set
            course: Optional course context
            
        Returns:
            UserProblemSetProgress instance
        """
        progress, _ = ProgressRepository.get_or_create_problem_set_progress(
            user, problem_set, course
        )
        return progress
    
    @staticmethod
    def get_user_progress_for_problem(
        user: 'User',
        problem: 'Problem',
        course: Optional['Course'] = None,
        problem_set: Optional['ProblemSet'] = None
    ) -> 'UserProgress':
        """
        Get user's progress for a specific problem.

        Args:
            user: The user
            problem: The problem
            course: Optional course context
            problem_set: Optional problem set context

        Returns:
            UserProgress instance or None
        """
        return ProgressRepository.get_user_progress(user, problem, course, problem_set)
    
    @staticmethod
    def get_user_all_progress(
        user: 'User',
        course: Optional['Course'] = None
    ) -> 'models.QuerySet':
        """
        Get all progress records for a user.
        
        Args:
            user: The user
            course: Optional course context
            
        Returns:
            QuerySet of UserProgress instances
        """
        return ProgressRepository.get_user_all_progress(user, course)
    
    @staticmethod
    def get_course_problem_set_progress(
        user: 'User',
        course: 'Course'
    ) -> 'models.QuerySet':
        """
        Get all problem set progress for a user in a course.
        
        Args:
            user: The user
            course: The course
            
        Returns:
            QuerySet of UserProblemSetProgress instances
        """
        return ProgressRepository.get_user_problem_set_progresses(user, course)
    
    @staticmethod
    def format_problems_progress(problems_with_progress: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format problems progress data for API response.
        
        Args:
            problems_with_progress: List of problems with progress data
            
        Returns:
            Formatted list of problem progress dicts
        """
        problems_progress = []
        for item in problems_with_progress:
            progress_data = {
                'problem_slug': item['problem'].slug,
                'problem_title': item['problem'].title,
                'order': item['order'],
                'status': item['status'],
                'best_score': item['best_score'],
                'attempts': item['attempts'],
            }
            # Include segmentation_passed if available
            if 'segmentation_passed' in item:
                progress_data['segmentation_passed'] = item['segmentation_passed']
            problems_progress.append(progress_data)
        
        # Sort by order
        problems_progress.sort(key=lambda x: x['order'])
        return problems_progress
    
    @staticmethod
    def format_course_progress_summary(progresses: List) -> Dict[str, List[Dict[str, Any]]]:
        """
        Format course progress summary data for API response.
        
        Args:
            progresses: List of UserProblemSetProgress instances
            
        Returns:
            Dict mapping course IDs to formatted progress data
        """
        course_data = {}
        for progress in progresses:
            course_id = progress.course.course_id if progress.course else 'no_course'
            if course_id not in course_data:
                course_data[course_id] = {
                    'course_name': progress.course.name if progress.course else 'No Course',
                    'problem_sets': []
                }
            course_data[course_id]['problem_sets'].append({
                'problem_set_slug': progress.problem_set.slug,
                'problem_set_title': progress.problem_set.title,
                'completed_problems': progress.completed_problems,
                'total_problems': progress.total_problems,
                'completion_percentage': progress.completion_percentage,
                'is_completed': progress.is_completed,
                'last_activity': progress.last_activity,
            })
        return course_data
    
    @staticmethod
    @transaction.atomic
    def _update_problem_set_progress(
        user_id: int,
        problem_set_id: int,
        course_id: Optional[int] = None
    ):
        """Update problem set progress based on individual problem progress."""
        try:
            # Get or create problem set progress with locking
            set_progress, _ = ProgressRepository.get_or_create_problem_set_with_lock(
                user_id=user_id,
                problem_set_id=problem_set_id,
                course_id=course_id
            )
            
            # Calculate aggregate metrics
            problem_progress = ProgressRepository.get_problem_set_progress_aggregate(
                user_id=user_id,
                problem_set_id=problem_set_id,
                course_id=course_id
            )
            
            # Update set progress
            set_progress.total_problems = problem_progress['total'] or 0
            set_progress.completed_problems = problem_progress['completed'] or 0
            set_progress.in_progress_problems = problem_progress['in_progress'] or 0
            set_progress.average_score = problem_progress['avg_score'] or 0
            
            if set_progress.total_problems > 0:
                set_progress.completion_percentage = int(
                    (set_progress.completed_problems / set_progress.total_problems) * 100
                )
                set_progress.is_completed = (
                    set_progress.completed_problems == set_progress.total_problems
                )
            
            set_progress.last_activity = datetime.now()
            set_progress.save()
            
            # Invalidate problem set cache
            cache_key = f'user_progress:set:{problem_set_id}:{user_id}'
            cache.delete(cache_key)
            
        except Exception as e:
            logger.error(f"Error updating problem set progress: {str(e)}")
    
    @staticmethod
    def _invalidate_progress_cache(
        user_id: int,
        problem_id: Optional[int] = None,
        problem_set_id: Optional[int] = None
    ):
        """Invalidate relevant cache entries after progress update."""
        cache_keys = [
            f'user_progress_all:{user_id}',
        ]
        
        if problem_id:
            cache_keys.append(f'user_progress:{user_id}:problem:{problem_id}')
        
        if problem_set_id:
            cache_keys.append(f'user_progress:{user_id}:set:{problem_set_id}')
        
        cache.delete_many(cache_keys)
    
    @staticmethod
    def get_user_summary(user_id: int) -> Dict[str, Any]:
        """
        Get comprehensive summary of user's progress across all courses.
        Uses caching to reduce database load.
        """
        cache_key = f'user_progress_summary:{user_id}'
        summary = cache.get(cache_key)
        
        if summary is None:
            # Build summary from database
            course_progresses = ProgressRepository.get_course_progress_summary_data(
                user_id=user_id
            )
            
            course_data = {}
            total_problems = 0
            total_completed = 0
            
            for progress in course_progresses:
                course_id = progress['course_id']
                if course_id not in course_data:
                    course_data[course_id] = {
                        'course_name': progress['course_name'],
                        'problem_sets': []
                    }
                
                course_data[course_id]['problem_sets'].append({
                    'problem_set_slug': progress['problem_set_slug'],
                    'problem_set_title': progress['problem_set_title'],
                    'completed_problems': progress['completed_problems'],
                    'total_problems': progress['total_problems'],
                    'completion_percentage': progress['completion_percentage'],
                    'is_completed': progress['is_completed'],
                    'last_activity': progress['last_activity'],
                })
                
                total_problems += progress['total_problems']
                total_completed += progress['completed_problems']
            
            summary = {
                'overall': {
                    'total_problems': total_problems,
                    'completed_problems': total_completed,
                    'completion_percentage': int(
                        (total_completed / total_problems * 100) if total_problems > 0 else 0
                    ),
                },
                'courses': course_data
            }
            
            # Cache for 10 minutes
            cache.set(cache_key, summary, 600)
        
        return summary
    
    @staticmethod
    def get_progress_context(user_id: int, problem_slug: str, 
                           problem_set_slug: Optional[str] = None,
                           course_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get complete progress context with validation.
        
        Args:
            user_id: User ID
            problem_slug: Problem slug
            problem_set_slug: Optional problem set slug
            course_id: Optional course ID
            
        Returns:
            Dict with problem, problem_set, course, and progress data
            
        Raises:
            ValueError: If required entities not found
        """
        try:
            # Get problem
            problem = ProblemRepository.get_problem_by_slug(problem_slug)
            if not problem:
                raise ValueError(f'Problem {problem_slug} not found')
            
            # Get problem set if provided
            problem_set = None
            if problem_set_slug:
                problem_set = ProblemRepository.get_problem_set_by_slug(problem_set_slug)
                if not problem_set:
                    raise ValueError(f'Problem set {problem_set_slug} not found')
            
            # Get course if provided
            course = None
            if course_id:
                try:
                    course = CourseRepository.get_course_by_id(course_id)
                except Exception:
                    # Course validation is optional in this context
                    pass
            
            # Get progress
            progress = None
            if problem_set and course:
                progress = ProgressRepository.filter_by_ids(
                    user_id=user_id,
                    problem_id=problem.id
                ).filter(
                    problem_set=problem_set,
                    course=course
                ).first()
            elif problem_set:
                progress = ProgressRepository.filter_by_ids(
                    user_id=user_id,
                    problem_id=problem.id
                ).filter(
                    problem_set=problem_set
                ).first()
            else:
                progress = ProgressRepository.filter_by_ids(
                    user_id=user_id,
                    problem_id=problem.id
                ).first()
            
            return {
                'problem': problem,
                'problem_set': problem_set,
                'course': course,
                'progress': progress
            }
            
        except Exception:
            raise ValueError(str(e))
    
    @staticmethod
    def get_problem_set_progress_with_context(user, problem_set_slug: str,
                                            course_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get problem set progress with full context validation.
        
        Args:
            user: Django User instance
            problem_set_slug: Problem set slug
            course_id: Optional course ID
            
        Returns:
            Dict with progress data and context
        """
        try:
            # Get problem set
            problem_set = ProblemRepository.get_problem_set_by_slug(problem_set_slug)
            if not problem_set:
                raise ValueError(f'Problem set {problem_set_slug} not found')
            
            # Get course if provided
            course = None
            if course_id:
                try:
                    course = CourseRepository.get_course_by_id(course_id)
                except Exception:
                    pass
            
            # Get or create problem set progress
            if course:
                progress, _ = ProgressRepository.get_or_create_problem_set_progress(
                    user, problem_set, course
                )
                if progress.total_problems == 0:
                    progress.total_problems = ProblemRepository.count_problems_in_set(problem_set)
                    progress.save()
            else:
                progress, _ = ProgressRepository.get_or_create_problem_set_progress(
                    user, problem_set, None
                )
                if progress.total_problems == 0:
                    progress.total_problems = ProblemRepository.count_problems_in_set(problem_set)
                    progress.save()
            
            # Get all problems in the set with user progress
            problems_with_progress = []
            for membership in ProblemSetMembershipRepository.get_problem_set_memberships(problem_set):
                problem = membership.problem
                # Get user progress for this specific context
                user_progress = ProgressRepository.get_user_progress(
                    user, problem, course, problem_set
                )

                # Get last submission to include segmentation_passed
                last_submission = None
                segmentation_passed = None
                if user_progress:
                    # Import new submission model for querying
                    from purplex.submissions.models import Submission
                    last_submission = Submission.objects.filter(
                        user=user,
                        problem=problem,
                        course=course
                    ).order_by('-submitted_at').first()
                    if last_submission and hasattr(last_submission, 'segmentation'):
                        segmentation_passed = last_submission.segmentation.passed if last_submission.segmentation else None

                problems_with_progress.append({
                    'problem': problem,
                    'order': membership.order,
                    'progress': user_progress,
                    'status': user_progress.status if user_progress else 'not_started',
                    'best_score': user_progress.best_score if user_progress else 0,
                    'attempts': user_progress.attempts if user_progress else 0,
                    'segmentation_passed': segmentation_passed
                })
            
            return {
                'problem_set': problem_set,
                'course': course,
                'progress': progress,
                'problems_with_progress': problems_with_progress,
                'completion_percentage': progress.completion_percentage,
                'completed_problems': progress.completed_problems,
                'total_problems': progress.total_problems
            }
            
        except Exception as e:
            if 'not found' in str(e):
                raise
            raise ValueError(f'Error getting problem set progress: {str(e)}')
    
    @staticmethod
    def get_last_submission_with_context(user, problem_slug: str,
                                       problem_set_slug: Optional[str] = None,
                                       course_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get last submission with clean data transformation.

        Args:
            user: Django User instance
            problem_slug: Problem slug
            problem_set_slug: Optional problem set slug
            course_id: Optional course ID

        Returns:
            Dict with properly formatted submission data
        """
        # Get problem
        problem = ProblemRepository.get_problem_by_slug(problem_slug)
        if not problem:
            return {
                'problem': None,
                'submission': None,
                'has_submission': False
            }

        # Get problem set if provided
        problem_set = None
        if problem_set_slug:
            problem_set = ProblemRepository.get_problem_set_by_slug(problem_set_slug)

        # Get course if provided
        course = None
        if course_id:
            course = CourseRepository.get_course_by_id(course_id)

        # Get last submission using new model
        from purplex.submissions.models import Submission

        # Build filter with proper context - MUST include problem_set to prevent cross-set leakage
        filters = {
            'user': user,
            'problem': problem,
        }

        # Add problem_set filter if provided - this is critical to prevent seeing submissions from other sets
        if problem_set:
            filters['problem_set'] = problem_set

        # Add course filter if provided
        if course:
            filters['course'] = course

        submission = Submission.objects.filter(
            **filters
        ).order_by('-submitted_at').first()

        return {
            'problem': problem,
            'problem_set': problem_set,
            'course': course,
            'submission': submission,
            'has_submission': submission is not None
        }

    @staticmethod
    def _extract_variations(submission):
        """Extract code variations for EiPL, single code for direct."""
        if submission.submission_type == 'eipl':
            variations = submission.code_variations.all().order_by('variation_index')
            return [v.generated_code for v in variations]
        elif submission.processed_code:
            return [submission.processed_code]
        return []

    @staticmethod
    def _extract_test_results(submission, problem):
        """Transform TestExecution objects to frontend format."""
        results = []

        if submission.submission_type == 'eipl':
            # Group test results by code variation
            variations = submission.code_variations.all().order_by('variation_index')
            for variation in variations:
                test_execs = variation.test_executions.all().order_by('execution_order')
                var_results = []

                # If we have TestExecution records, use them
                if test_execs.exists():
                    for test_exec in test_execs:
                        var_results.append({
                            'isSuccessful': test_exec.passed,
                            'function_call': ProgressService._format_function_call(
                                problem.function_name, test_exec.input_values
                            ),
                            'expected_output': test_exec.expected_output,
                            'actual_output': test_exec.actual_output,  # Let frontend handle null values
                            'error': test_exec.error_message
                        })
                # Fallback: If no TestExecution records exist but we have summary data
                elif variation.tests_total > 0:
                    # We don't have individual test details, but we can show summary
                    # Create placeholder results based on the summary
                    for i in range(variation.tests_total):
                        is_passed = i < variation.tests_passed
                        var_results.append({
                            'isSuccessful': is_passed,
                            'function_call': f"{problem.function_name}(test_case_{i+1})",
                            'expected_output': 'Test details not available',
                            'actual_output': 'Passed' if is_passed else 'Failed',
                            'error': '' if is_passed else 'Test failed (details not available)'
                        })

                results.append({
                    'success': variation.tests_passed == variation.tests_total and variation.tests_total > 0,
                    'testsPassed': variation.tests_passed,
                    'totalTests': variation.tests_total,
                    'test_results': var_results,
                    'results': var_results  # Duplicate for frontend compatibility
                })
        else:
            # Direct code submission - single result set
            test_execs = submission.test_executions.all().order_by('execution_order')
            all_results = []

            for test_exec in test_execs:
                all_results.append({
                    'isSuccessful': test_exec.passed,
                    'function_call': ProgressService._format_function_call(
                        problem.function_name, test_exec.input_values
                    ),
                    'expected_output': test_exec.expected_output,
                    'actual_output': test_exec.actual_output,  # Let frontend handle null values
                    'error': test_exec.error_message
                })

            tests_passed = submission.test_executions.filter(passed=True).count()
            tests_total = submission.test_executions.count()

            results.append({
                'success': tests_passed == tests_total and tests_total > 0,
                'testsPassed': tests_passed,
                'totalTests': tests_total,
                'test_results': all_results,
                'results': all_results  # Duplicate for frontend compatibility
            })

        return results

    @staticmethod
    def _format_function_call(function_name, input_values):
        """Format a function call string from function name and input values."""
        import json
        if isinstance(input_values, list):
            # Use json.dumps for strings to ensure proper quoting, repr for others
            args = ', '.join(json.dumps(v) if isinstance(v, str) else repr(v) for v in input_values)
        else:
            # Single value case
            args = json.dumps(input_values) if isinstance(input_values, str) else repr(input_values)
        return f"{function_name}({args})"

    @staticmethod
    def _extract_segmentation(submission):
        """Extract segmentation data only if segmentation is enabled for the problem."""
        if (hasattr(submission, 'segmentation') and submission.segmentation and
            submission.problem.segmentation_enabled):
            seg = submission.segmentation
            return {
                'segments': seg.segments,
                'segment_count': seg.segment_count,
                'comprehension_level': seg.comprehension_level,
                'feedback': seg.feedback_message,
                'passed': seg.passed
            }
        return None

    @staticmethod
    def _calculate_passing_variations(submission):
        """Calculate number of passing variations."""
        from django.db import models
        if submission.submission_type == 'eipl':
            return submission.code_variations.filter(
                tests_passed=models.F('tests_total'),
                tests_total__gt=0
            ).count()
        elif submission.passed_all_tests:
            return 1
        return 0

    @staticmethod
    def _count_variations(submission):
        """Count total variations."""
        if submission.submission_type == 'eipl':
            return submission.code_variations.count()
        elif submission.processed_code:
            return 1
        return 0

    @staticmethod
    def _check_segmentation_passed(submission):
        """Check if segmentation passed (good comprehension)."""
        if hasattr(submission, 'segmentation'):
            return submission.segmentation.passed
        return None