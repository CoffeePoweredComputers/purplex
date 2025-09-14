"""
Service for managing submission-related business logic.
"""

import logging
from typing import Dict, Any, Optional, List
from django.db.models import Q
from django.contrib.auth.models import User

from purplex.problems_app.repositories import (
    SubmissionRepository,
    ProblemRepository, 
    CourseRepository
)
from purplex.submissions_app.models import PromptSubmission
from purplex.problems_app.models import Problem, Course

logger = logging.getLogger(__name__)


class SubmissionService:
    """Handle all submission-related business logic."""
    
    @staticmethod
    def get_all_submissions(search: str = '', status_filter: str = '', 
                           problem_set_filter: str = '') -> List[PromptSubmission]:
        """
        Get all submissions with optional filtering.
        
        Args:
            search: Search string for username, problem title, or problem set title
            status_filter: Filter by status (passed, partial, failed)
            problem_set_filter: Filter by problem set title
            
        Returns:
            List of filtered submissions
        """
        # Get filtered submissions from repository
        return SubmissionRepository.get_filtered_submissions(
            search=search,
            status_filter=status_filter,
            problem_set_filter=problem_set_filter
        )
    
    @staticmethod
    def get_submission_detail(submission_id: int) -> Optional[PromptSubmission]:
        """
        Get detailed submission data.
        
        Args:
            submission_id: ID of the submission
            
        Returns:
            PromptSubmission instance or None
        """
        return SubmissionRepository.get_submission_by_id(submission_id)
    
    @staticmethod
    def delete_submission(submission_id: int) -> bool:
        """
        Delete a submission.
        
        Args:
            submission_id: ID of the submission to delete
            
        Returns:
            True if deleted, False if not found
        """
        return SubmissionRepository.delete(id=submission_id)[0] > 0
    
    @staticmethod
    def calculate_submission_status(score: float) -> str:
        """
        Calculate submission status based on score.
        
        Args:
            score: Submission score
            
        Returns:
            Status string (passed, partial, or failed)
        """
        if score >= 100:
            return 'passed'
        elif score > 0:
            return 'partial'
        else:
            return 'failed'
    
    @staticmethod
    def format_submission_for_export(submission: PromptSubmission) -> Dict[str, Any]:
        """
        Format a submission for export with all details.
        
        Args:
            submission: PromptSubmission instance
            
        Returns:
            Dictionary with formatted submission data
        """
        status = SubmissionService.calculate_submission_status(submission.score)
        
        return {
            'id': submission.id,
            'user': submission.user.username,
            'problem': submission.problem.title,
            'problem_set': submission.problem_set.title if submission.problem_set else 'Unknown',
            'course': submission.course.course_id if submission.course else None,
            'score': submission.score,
            'status': status,
            'submitted_at': submission.submitted_at.isoformat() if submission.submitted_at else '',
            'prompt': submission.prompt or '',
            
            # Submission field structure
            'code_variations': submission.code_variations or [],
            'test_results': submission.test_results or [],
            'passing_variations': submission.passing_variations or 0,
            'total_variations': submission.total_variations or 0,
            'execution_time': submission.execution_time,
            'time_spent': str(submission.time_spent) if submission.time_spent else None
        }
    
    @staticmethod
    def get_submissions_for_export(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get submissions formatted for CSV export.
        
        Args:
            filters: Dictionary with filter criteria
            
        Returns:
            List of formatted submission data
        """
        # Get filtered submissions
        search = filters.get('search', '').strip()
        status_filter = filters.get('status', '').strip()
        problem_set_filter = filters.get('problem_set', '').strip()
        
        submissions = SubmissionService.get_all_submissions(
            search=search,
            status_filter=status_filter,
            problem_set_filter=problem_set_filter
        )
        
        # Format for export
        export_data = []
        for submission in submissions:
            export_data.append(SubmissionService.format_submission_for_export(submission))
        
        return export_data
    
    @staticmethod
    def get_user_last_submission(user: User, problem_slug: str, 
                                course_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get user's most recent submission for a problem.
        
        Args:
            user: User instance
            problem_slug: Problem slug
            course_id: Optional course ID for context
            
        Returns:
            Dictionary with submission data or None
        """
        # Get the problem
        problem = ProblemRepository.get_problem_by_slug(problem_slug)
        if not problem:
            return None
        
        # Get the course if specified
        course = None
        if course_id:
            course = CourseRepository.get_course_by_id(course_id)
            if not course:
                return None
        
        # Get the last submission
        submission = SubmissionRepository.get_last_submission(user, problem, course)
        
        if not submission:
            return None
        
        # Format response
        return {
            'has_submission': True,
            'submission_id': submission.id,
            'score': submission.score,
            'variations': submission.code_variations,
            'results': submission.test_results,
            'passing_variations': submission.passing_variations,
            'submitted_at': submission.submitted_at.isoformat() if submission.submitted_at else None,
            'user_prompt': submission.prompt,
            'segmentation_passed': submission.segmentation_passed
        }
    
    @staticmethod
    def format_submission_for_list(submission: PromptSubmission) -> Dict[str, Any]:
        """
        Format a submission for list display.
        
        Args:
            submission: PromptSubmission instance
            
        Returns:
            Dictionary with formatted submission data for list view
        """
        status = SubmissionService.calculate_submission_status(submission.score)
        
        return {
            'id': submission.id,
            'user': submission.user.username,
            'problem': submission.problem.title,
            'problem_set': submission.problem_set.title if submission.problem_set else 'Unknown',
            'score': submission.score,
            'status': status,
            'submitted_at': submission.submitted_at,
        }
    
    @staticmethod
    def get_submission_statistics(problem_slug: Optional[str] = None,
                                 user: Optional[User] = None,
                                 course: Optional[Course] = None) -> Dict[str, Any]:
        """
        Get submission statistics.
        
        Args:
            problem_slug: Optional problem slug to filter by
            user: Optional user to filter by
            course: Optional course to filter by
            
        Returns:
            Dictionary with submission statistics
        """
        if problem_slug:
            problem = ProblemRepository.get_problem_by_slug(problem_slug)
            if problem:
                return SubmissionRepository.get_submission_statistics(problem)
        
        if user:
            return SubmissionRepository.get_user_submission_statistics(user, course)
        
        # Return general statistics - should be done in repository
        all_submissions = SubmissionRepository.get_all_with_relations()
        total_submissions = len(all_submissions)
        passed_submissions = sum(1 for s in all_submissions if s.score >= 100)
        unique_users = len(set(s.user_id for s in all_submissions))
        unique_problems = len(set(s.problem_id for s in all_submissions))
        
        return {
            'total_submissions': total_submissions,
            'passed_submissions': passed_submissions,
            'pass_rate': (passed_submissions / total_submissions * 100) if total_submissions > 0 else 0,
            'unique_users': unique_users,
            'unique_problems': unique_problems
        }