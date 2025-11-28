"""Service for managing user progress with transaction safety and caching."""

import logging
import time
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from datetime import datetime, timedelta
from django.core.cache import cache
from django.db import transaction, IntegrityError, DatabaseError
from django.utils import timezone

from purplex.submissions.grading_service import GradingService
from problems_app.handlers import get_handler

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
            from purplex.submissions.models import Submission

            # Prefetch user progress for all problems in this set (single query)
            progress_qs = ProgressRepository.filter_by_ids(
                user_id=user.id
            ).filter(
                problem_set=problem_set,
                course=course
            ).select_related('problem')

            # Prefetch latest submissions with segmentation (single query)
            latest_submissions_qs = Submission.objects.filter(
                user=user,
                problem_set=problem_set,
                course=course
            ).select_related('problem').prefetch_related('segmentation').order_by(
                'problem__id', '-submitted_at'
            ).distinct('problem__id')

            # Build lookup dictionaries for O(1) access
            progress_by_problem = {p.problem_id: p for p in progress_qs}
            submissions_by_problem = {s.problem_id: s for s in latest_submissions_qs}

            # Now iterate with O(1) lookups instead of N queries
            problems_with_progress = []
            for membership in ProblemSetMembershipRepository.get_problem_set_memberships(problem_set):
                problem = membership.problem

                # O(1) dictionary lookup instead of database query
                user_progress = progress_by_problem.get(problem.id)
                last_submission = submissions_by_problem.get(problem.id)

                # Extract segmentation data if available
                segmentation_passed = None
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

        # CRITICAL FIX: Prefetch related data to prevent N+1 queries when accessing variations
        submission = Submission.objects.filter(
            **filters
        ).prefetch_related(
            'test_executions__test_case',
            'code_variations__test_executions__test_case',
            'segmentation'
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
        """Extract code variations by delegating to the appropriate handler."""
        handler = get_handler(submission.submission_type)
        return handler.extract_variations(submission)

    @staticmethod
    def _extract_test_results(submission, problem):
        """Transform TestExecution objects to frontend format by delegating to handler."""
        handler = get_handler(submission.submission_type)
        return handler.extract_test_results(submission, problem)

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
        """Calculate number of passing variations by delegating to handler."""
        handler = get_handler(submission.submission_type)
        return handler.count_passing_variations(submission)

    @staticmethod
    def _count_variations(submission):
        """Count total variations by delegating to handler."""
        handler = get_handler(submission.submission_type)
        return handler.count_variations(submission)

    @staticmethod
    def _check_segmentation_passed(submission):
        """Check if segmentation passed (good comprehension)."""
        if hasattr(submission, 'segmentation'):
            return submission.segmentation.passed
        return None

    # ==========================================================================
    # WRITE METHODS (consolidated from ProgressEngine)
    # ==========================================================================

    @staticmethod
    def process_submission(submission) -> 'UserProgress':
        """
        Main entry point for processing any submission's impact on progress.
        This is the ONLY method that should update UserProgress records.

        Args:
            submission: A Submission model instance

        Returns:
            The updated UserProgress instance
        """
        from ..models import UserProgress, UserProblemSetProgress

        logger.info(f"[ProgressService] Processing submission {submission.submission_id}")
        logger.info(f"[ProgressService] User: {submission.user.username}, Problem: {submission.problem.slug}")
        logger.info(f"[ProgressService] Score: {submission.score}, Problem Set: {submission.problem_set.slug if submission.problem_set else 'None'}")

        with transaction.atomic():
            # Get or create progress record with full context
            progress = ProgressService._get_or_create_progress_for_submission(submission)

            # Calculate all progress metrics
            old_status = progress.status
            old_score = progress.best_score

            # Update core metrics
            ProgressService._update_scores(progress, submission)
            ProgressService._update_timing(progress, submission)
            ProgressService._update_attempts(progress, submission)

            # Evaluate completion and grade using GradingService
            grade = GradingService.calculate_grade(submission)
            status = ProgressService._evaluate_status(submission, progress)

            # Update progress fields
            progress.grade = grade
            progress.status = status

            # Update completion fields based on status
            if status == 'completed':
                progress.is_completed = True
                progress.completion_percentage = 100
                if not progress.completed_at:
                    progress.completed_at = timezone.now()
                    if progress.first_attempt:
                        progress.days_to_complete = (progress.completed_at - progress.first_attempt).days
            elif status == 'in_progress':
                progress.is_completed = False
                # Use best score for percentage, but cap at 99 if not complete
                progress.completion_percentage = min(progress.best_score, 99)
            else:  # not_started
                progress.is_completed = False
                progress.completion_percentage = 0

            # Update hints used
            if hasattr(submission, 'hint_activations'):
                progress.hints_used = submission.hint_activations.count()

            # Log changes
            if old_status != status:
                logger.info(f"[ProgressService] Status changed: {old_status} -> {status}")
            if old_score != progress.best_score:
                logger.info(f"[ProgressService] Best score changed: {old_score} -> {progress.best_score}")

            logger.info(f"[ProgressService] Saving progress - is_completed: {progress.is_completed}, status: {status}, grade: {grade}")

            # PERFORMANCE: Single save for all progress updates
            progress.save()

            # CRITICAL: Invalidate cache after update
            ProgressService._invalidate_progress_cache(
                user_id=progress.user.id,
                problem_id=progress.problem.id,
                problem_set_id=progress.problem_set.id if progress.problem_set else None
            )

            # Update problem set progress (single query)
            if submission.problem_set:
                UserProblemSetProgress.update_from_progress(progress)

            # CREATE DAILY SNAPSHOT FOR LONGITUDINAL TRACKING
            ProgressService._create_daily_snapshot(progress, submission)

            # Emit SSE event for real-time updates
            ProgressService._emit_progress_event(progress, submission)

            logger.info(f"[ProgressService] Completed processing submission {submission.submission_id}")

            return progress

    @staticmethod
    def _get_or_create_progress_for_submission(submission) -> 'UserProgress':
        """Get or create UserProgress record with row-level locking, handling migration of old records."""
        from ..models import UserProgress

        # Initialize created flag to prevent UnboundLocalError
        created = False

        # CRITICAL: Use row-level locking to prevent race conditions at scale
        # This prevents lost updates when multiple concurrent submissions occur
        try:
            # First, try to get existing progress with SELECT FOR UPDATE lock
            # Use nowait=True to fail fast instead of blocking indefinitely
            lock_start = time.time()
            try:
                progress = UserProgress.objects.select_for_update(nowait=True).filter(
                    user=submission.user,
                    problem=submission.problem,
                    problem_set=submission.problem_set,
                    course=submission.course,
                ).first()
                lock_duration = time.time() - lock_start
                if lock_duration > 0.1:  # Log if lock acquisition took >100ms
                    logger.info(f"[ProgressService] Lock acquired in {lock_duration:.3f}s")
            except DatabaseError as e:
                lock_duration = time.time() - lock_start
                logger.warning(f"[ProgressService] Progress locked by another request after {lock_duration:.3f}s: {e}")
                # Retry once with a small delay
                time.sleep(0.1)
                progress = UserProgress.objects.select_for_update(nowait=True).filter(
                    user=submission.user,
                    problem=submission.problem,
                    problem_set=submission.problem_set,
                    course=submission.course,
                ).first()

            if progress:
                logger.info(f"[ProgressService] Progress record FOUND with ID: {progress.id} (LOCKED)")
                created = False
            else:
                # No existing record, create new one
                # Note: There's still a small race window here, so we catch IntegrityError
                try:
                    progress = UserProgress.objects.create(
                        user=submission.user,
                        problem=submission.problem,
                        problem_set=submission.problem_set,
                        course=submission.course,
                        problem_version=submission.problem.version
                    )
                    logger.info(f"[ProgressService] Progress record CREATED with ID: {progress.id}")
                    created = True
                except IntegrityError:
                    # Race condition: another request created it between our check and create
                    # Retry with lock to get the newly created record
                    progress = UserProgress.objects.select_for_update(nowait=True).get(
                        user=submission.user,
                        problem=submission.problem,
                        problem_set=submission.problem_set,
                        course=submission.course,
                    )
                    logger.info(f"[ProgressService] Progress record FOUND after race condition with ID: {progress.id} (LOCKED)")
                    created = False
        except DatabaseError as e:
            logger.error(f"[ProgressService] Database lock error after retries: {str(e)}")
            raise ValueError("Your progress is currently being updated by another submission. Please try again in a moment.")
        except Exception as e:
            logger.error(f"[ProgressService] Error getting/creating progress: {str(e)}")
            raise

        # Handle migration of old records without problem_set
        if created and submission.problem_set:
            try:
                # Look for existing progress without problem_set context
                old_progress = UserProgress.objects.get(
                    user=submission.user,
                    problem=submission.problem,
                    problem_set__isnull=True,
                    course=submission.course if submission.course else None
                )

                logger.info(f"[ProgressService] Migrating old progress record without problem_set")

                # Migrate all relevant fields
                progress.attempts = old_progress.attempts
                progress.best_score = old_progress.best_score
                progress.average_score = old_progress.average_score
                progress.status = old_progress.status
                progress.is_completed = old_progress.is_completed
                progress.completion_percentage = old_progress.completion_percentage
                progress.first_attempt = old_progress.first_attempt
                progress.last_attempt = old_progress.last_attempt
                progress.completed_at = old_progress.completed_at
                progress.total_time_spent = old_progress.total_time_spent
                progress.hints_used = old_progress.hints_used
                progress.days_to_complete = old_progress.days_to_complete
                progress.grade = getattr(old_progress, 'grade', 'incomplete')

                # Save migrated progress and delete old
                progress.save()
                old_progress.delete()
                logger.info(f"[ProgressService] Migration complete, old record deleted")

            except UserProgress.DoesNotExist:
                pass  # No old progress to migrate
            except UserProgress.MultipleObjectsReturned:
                logger.warning(f"[ProgressService] Multiple old progress records found for user {submission.user.username}")

        return progress

    @staticmethod
    def _update_scores(progress, submission):
        """Update score-related fields."""
        # Update best score
        if submission.score > progress.best_score:
            progress.best_score = submission.score
            logger.info(f"[ProgressService] Updated best score to {progress.best_score}")

        # Update average score
        if progress.attempts > 0:
            # Account for the new attempt that will be added
            progress.average_score = (
                (progress.average_score * progress.attempts + submission.score)
                / (progress.attempts + 1)
            )

    @staticmethod
    def _update_timing(progress, submission):
        """Update timing-related fields."""
        # Set timestamps
        if not progress.first_attempt:
            progress.first_attempt = submission.submitted_at
        progress.last_attempt = submission.submitted_at

        # Update time spent if available
        if hasattr(submission, 'time_spent') and submission.time_spent:
            progress.total_time_spent += submission.time_spent

    @staticmethod
    def _update_attempts(progress, submission):
        """Update attempt counters."""
        progress.attempts += 1

        # Update successful attempts if this is a perfect score
        if submission.score == 100:
            progress.successful_attempts = getattr(progress, 'successful_attempts', 0) + 1
            progress.consecutive_successes = getattr(progress, 'consecutive_successes', 0) + 1
        else:
            progress.consecutive_successes = 0

    @staticmethod
    def _evaluate_status(submission, progress) -> str:
        """
        Evaluate the overall progress status.
        This is the ONE place where completion is determined.

        Returns:
            'not_started', 'in_progress', or 'completed'
        """
        if progress.attempts == 0:
            return 'not_started'

        # For completion, we need grade to be 'complete'
        grade = GradingService.calculate_grade(submission)

        # Check if ANY submission for this problem has achieved 'complete' grade
        # This prevents regression - once completed, always completed
        if grade == 'complete' or progress.is_completed:
            return 'completed'

        # Otherwise, we're in progress
        return 'in_progress'

    @staticmethod
    def _evaluate_completion(submission) -> bool:
        """
        Simple completion check for a single submission.
        Used internally and can be called externally if needed.

        Returns:
            True if submission meets completion criteria, False otherwise
        """
        handler = get_handler(submission.submission_type)
        result = handler.evaluate_completion(submission, submission.problem)
        return result == 'complete'

    @staticmethod
    def _create_daily_snapshot(progress, submission):
        """
        Create or update daily progress snapshot for longitudinal tracking.

        This enables research on learning curves and student progress over time.
        Snapshots are unique per (user, problem, problem_set, date).
        """
        from ..models import ProgressSnapshot

        today = timezone.now().date()

        # Calculate time spent today (if this is the first submission today, use full time)
        time_spent_today = submission.time_spent or timedelta(0)

        # Get or update today's snapshot
        snapshot, created = ProgressSnapshot.objects.update_or_create(
            user=progress.user,
            problem=progress.problem,
            problem_set=progress.problem_set,
            snapshot_date=today,
            defaults={
                'completion_percentage': progress.completion_percentage,
                'problems_completed': 1 if progress.is_completed else 0,
                'average_score': progress.best_score,  # Use best score as the average for single problem
                'time_spent_today': time_spent_today
            }
        )

        if created:
            logger.info(f"[ProgressService] Created snapshot for {progress.user.username} on {progress.problem.slug}")
        else:
            logger.info(f"[ProgressService] Updated snapshot for {progress.user.username} on {progress.problem.slug}")

        return snapshot

    @staticmethod
    def _emit_progress_event(progress, submission):
        """
        Emit SSE event for real-time frontend updates.
        Maintains exact same event format that frontend expects.
        """
        logger.info(f"[ProgressService] SSE Event - Progress updated for {progress.user.username} on {progress.problem.slug}")

        # Store progress update in Redis for SSE views to poll
        # This follows the pattern used by the task SSE system
        try:
            # Create event data structure
            event_data = {
                'type': 'progress_update',
                'user_id': progress.user.id,
                'problem_slug': progress.problem.slug,
                'problem_set_slug': progress.problem_set.slug if progress.problem_set else None,
                'course_id': progress.course.id if progress.course else None,
                'status': progress.status,
                'best_score': progress.best_score,
                'attempts': progress.attempts,
                'is_completed': progress.is_completed,
                'grade': progress.grade,
                'submission_id': str(submission.submission_id) if hasattr(submission, 'submission_id') else None,
                'timestamp': timezone.now().isoformat()
            }

            # Store with expiry for cleanup (1 hour)
            key = f"progress:update:{progress.user.id}:{progress.problem.id}"
            cache.set(key, event_data, timeout=3600)

            # Progress events stored in cache for polling
            logger.debug(f"[ProgressService] Cached progress event with key: {key}")

        except Exception as e:
            # Don't fail the whole operation if SSE emission fails
            logger.error(f"[ProgressService] Failed to emit SSE event: {str(e)}")