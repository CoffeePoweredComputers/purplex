"""
Repository for submission-related model data access.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from django.db.models import Q, Count, Avg
from django.contrib.auth.models import User
from django.utils import timezone

from purplex.submissions_app.models import PromptSubmission, SegmentationResult
from purplex.problems_app.models import Problem, Course
from .base_repository import BaseRepository


class SubmissionRepository(BaseRepository):
    """
    Repository for all submission-related database queries.
    
    This repository handles all data access for prompt submissions,
    segmentation results, and submission analytics.
    """
    
    model_class = PromptSubmission
    
    @classmethod
    def get_all_with_relations(cls) -> List[PromptSubmission]:
        """
        Get all submissions with related data pre-fetched.
        
        Returns:
            List of PromptSubmission instances with related data
        """
        return cls.filter_with_select_related(
            select_fields=['user', 'problem', 'problem_set']
        )
    
    @classmethod
    def get_filtered_submissions(cls, search: str = '', status_filter: str = '', 
                                problem_set_filter: str = '') -> List[PromptSubmission]:
        """
        Get filtered submissions with all business logic applied.
        
        Args:
            search: Search string for username, problem title, or problem set title
            status_filter: Filter by status (passed, partial, failed)
            problem_set_filter: Filter by problem set title
            
        Returns:
            List of filtered PromptSubmission instances
        """
        # Build the queryset internally
        queryset = cls._build_optimized_queryset(
            select_related=['user', 'problem', 'problem_set'],
            order_by='-submitted_at'
        )
        
        # Apply search filter
        if search:
            queryset = queryset.filter(
                Q(user__username__icontains=search) |
                Q(problem__title__icontains=search) |
                Q(problem_set__title__icontains=search)
            )
        
        # Apply status filter based on score
        if status_filter:
            if status_filter == 'passed':
                queryset = queryset.filter(score__gte=100)
            elif status_filter == 'partial':
                queryset = queryset.filter(score__gt=0, score__lt=100)
            elif status_filter == 'failed':
                queryset = queryset.filter(score=0)
        
        # Apply problem set filter
        if problem_set_filter:
            queryset = queryset.filter(problem_set__title=problem_set_filter)
        
        # Convert to list before returning
        return list(queryset)
    
    @classmethod
    def get_submission_by_id(cls, submission_id: int) -> Optional[PromptSubmission]:
        """Get a submission by its ID."""
        return PromptSubmission.objects.filter(id=submission_id).first()
    
    @classmethod
    def get_submission_by_task_id(cls, task_id: str) -> Optional[PromptSubmission]:
        """Get a submission by its Celery task ID."""
        return PromptSubmission.objects.filter(task_id=task_id).first()
    
    @classmethod
    def get_user_submissions(cls, user: User, problem: Optional[Problem] = None,
                           course: Optional[Course] = None) -> List[PromptSubmission]:
        """
        Get all submissions for a user, optionally filtered by problem and course.
        
        Args:
            user: The user
            problem: Optional problem to filter by
            course: Optional course context
            
        Returns:
            List of submissions
        """
        filters = {'user': user}
        if problem:
            filters['problem'] = problem
        if course:
            filters['course'] = course
            
        return list(PromptSubmission.objects.filter(**filters).select_related(
            'problem', 'course'
        ).order_by('-created_at'))
    
    @classmethod
    def get_recent_submissions(cls, user: User, limit: int = 10) -> List[PromptSubmission]:
        """Get the most recent submissions for a user."""
        return list(PromptSubmission.objects.filter(
            user=user
        ).select_related(
            'problem', 'course'
        ).order_by('-created_at')[:limit])
    
    @classmethod
    def get_successful_submissions(cls, user: User, problem: Problem,
                                 course: Optional[Course] = None) -> List[PromptSubmission]:
        """Get all successful submissions for a user and problem."""
        filters = {
            'user': user,
            'problem': problem,
            'passed': True
        }
        if course:
            filters['course'] = course
            
        return list(PromptSubmission.objects.filter(**filters).order_by('-created_at'))
    
    @classmethod
    def count_user_submissions(cls, user: User, problem: Optional[Problem] = None,
                             course: Optional[Course] = None) -> int:
        """Count total submissions for a user."""
        filters = {'user': user}
        if problem:
            filters['problem'] = problem
        if course:
            filters['course'] = course
            
        return PromptSubmission.objects.filter(**filters).count()
    
    @classmethod
    def has_successful_submission(cls, user: User, problem: Problem,
                                course: Optional[Course] = None) -> bool:
        """Check if user has any successful submission for a problem."""
        filters = {
            'user': user,
            'problem': problem,
            'passed': True
        }
        if course:
            filters['course'] = course
            
        return PromptSubmission.objects.filter(**filters).exists()
    
    @classmethod
    def create_submission(cls, user: User, problem: Problem,
                        prompt: str, course: Optional[Course] = None,
                        **kwargs) -> PromptSubmission:
        """Create a new submission."""
        return PromptSubmission.objects.create(
            user=user,
            problem=problem,
            prompt=prompt,
            course=course,
            **kwargs
        )
    
    @classmethod
    def update_submission_status(cls, submission_id: int, status: str,
                               **additional_fields) -> bool:
        """
        Update the status of a submission.
        
        Args:
            submission_id: ID of the submission
            status: New status value
            **additional_fields: Additional fields to update
            
        Returns:
            True if updated, False if not found
        """
        update_fields = {'status': status, **additional_fields}
        updated = PromptSubmission.objects.filter(
            id=submission_id
        ).update(**update_fields)
        return updated > 0
    
    @classmethod
    def update_submission_result(cls, submission_id: int, passed: bool,
                               score: float, feedback: str,
                               generated_code: Optional[str] = None) -> bool:
        """Update submission with test results."""
        updates = {
            'passed': passed,
            'score': score,
            'feedback': feedback,
            'status': 'completed'
        }
        if generated_code:
            updates['generated_code'] = generated_code
            
        updated = PromptSubmission.objects.filter(
            id=submission_id
        ).update(**updates)
        return updated > 0
    
    @classmethod
    def get_pending_submissions(cls, max_age_minutes: int = 30) -> List[PromptSubmission]:
        """Get submissions that are still pending after a certain time."""
        cutoff_time = timezone.now() - timedelta(minutes=max_age_minutes)
        return list(PromptSubmission.objects.filter(
            status='pending',
            created_at__lt=cutoff_time
        ).select_related('user', 'problem'))
    
    @classmethod
    def get_submission_statistics(cls, problem: Problem) -> Dict[str, Any]:
        """
        Get submission statistics for a problem.
        
        Returns:
            Dictionary with submission statistics
        """
        submissions = PromptSubmission.objects.filter(problem=problem)
        
        return {
            'total_submissions': submissions.count(),
            'unique_users': submissions.values('user').distinct().count(),
            'success_rate': submissions.filter(
                passed=True
            ).count() / max(submissions.count(), 1),
            'avg_score': submissions.filter(
                score__isnull=False
            ).aggregate(Avg('score'))['score__avg'] or 0.0,
            'pending_count': submissions.filter(status='pending').count(),
            'failed_count': submissions.filter(status='failed').count()
        }
    
    @classmethod
    def get_user_submission_statistics(cls, user: User,
                                     course: Optional[Course] = None) -> Dict[str, Any]:
        """Get submission statistics for a user."""
        filters = {'user': user}
        if course:
            filters['course'] = course
            
        submissions = PromptSubmission.objects.filter(**filters)
        
        return {
            'total_submissions': submissions.count(),
            'successful_submissions': submissions.filter(passed=True).count(),
            'failed_submissions': submissions.filter(passed=False).count(),
            'pending_submissions': submissions.filter(status='pending').count(),
            'problems_attempted': submissions.values('problem').distinct().count(),
            'avg_score': submissions.filter(
                score__isnull=False
            ).aggregate(Avg('score'))['score__avg'] or 0.0
        }
    
    @classmethod
    def get_recent_activity_feed(cls, limit: int = 20) -> List[PromptSubmission]:
        """Get recent submission activity across all users."""
        return list(PromptSubmission.objects.filter(
            status='completed'
        ).select_related(
            'user', 'problem', 'course'
        ).order_by('-created_at')[:limit])
    
    @classmethod
    def delete_old_submissions(cls, days_old: int = 90) -> int:
        """Delete submissions older than specified days."""
        cutoff_date = timezone.now() - timedelta(days=days_old)
        deleted, _ = PromptSubmission.objects.filter(
            created_at__lt=cutoff_date
        ).delete()
        return deleted
    
    # Segmentation methods
    @classmethod
    def get_segmentation_result(cls, submission: PromptSubmission) -> Optional[SegmentationResult]:
        """Get segmentation result for a submission."""
        return SegmentationResult.objects.filter(
            submission=submission
        ).first()
    
    @classmethod
    def create_segmentation_result(cls, submission: PromptSubmission,
                                 **kwargs) -> SegmentationResult:
        """Create a segmentation result for a submission."""
        return SegmentationResult.objects.create(
            submission=submission,
            **kwargs
        )
    
    @classmethod
    def get_segmentations_for_problem(cls, problem: Problem) -> List[SegmentationResult]:
        """Get all segmentation results for a problem."""
        return list(SegmentationResult.objects.filter(
            submission__problem=problem
        ).select_related('submission', 'submission__user'))
    
    @classmethod
    def get_user_segmentations(cls, user: User) -> List[SegmentationResult]:
        """Get all segmentation results for a user."""
        return list(SegmentationResult.objects.filter(
            submission__user=user
        ).select_related('submission', 'submission__problem'))
    
    @classmethod
    def analyze_segmentation_patterns(cls, problem: Problem) -> Dict[str, Any]:
        """
        Analyze common segmentation patterns for a problem.
        
        Returns:
            Dictionary with pattern analysis
        """
        segmentations = SegmentationResult.objects.filter(
            submission__problem=problem
        )
        
        # This would require more complex analysis of the segments field
        # For now, return basic statistics
        return {
            'total_segmentations': segmentations.count(),
            'avg_segments': 0,  # Would need to analyze JSON field
            'common_patterns': []  # Would need pattern extraction logic
        }
    
    @classmethod
    def get_submissions_by_status(cls, status: str, limit: Optional[int] = None) -> List[PromptSubmission]:
        """Get submissions filtered by status."""
        queryset = PromptSubmission.objects.filter(
            status=status
        ).select_related('user', 'problem', 'course').order_by('-created_at')
        
        if limit:
            queryset = queryset[:limit]
            
        return list(queryset)
    
    @classmethod
    def mark_submission_as_failed(cls, submission_id: int, error_message: str) -> bool:
        """Mark a submission as failed with an error message."""
        updated = PromptSubmission.objects.filter(
            id=submission_id
        ).update(
            status='failed',
            feedback=error_message,
            passed=False
        )
        return updated > 0
    
    @classmethod
    def get_last_submission(cls, user: User, problem: Problem,
                           course: Optional[Course] = None) -> Optional[PromptSubmission]:
        """
        Get the most recent submission for a user and problem.
        
        Args:
            user: The user
            problem: The problem
            course: Optional course context
            
        Returns:
            Most recent PromptSubmission or None
        """
        filters = {
            'user': user,
            'problem': problem
        }
        if course:
            filters['course'] = course
            
        return PromptSubmission.objects.filter(**filters).order_by('-created_at').first()