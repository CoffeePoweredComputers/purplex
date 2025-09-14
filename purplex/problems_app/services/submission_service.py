"""Service for managing submissions with proper abstraction."""
from typing import Optional, Dict, Any, TYPE_CHECKING
from datetime import timedelta
from django.contrib.auth.models import User

from ..repositories import (
    SubmissionRepository, ProgressRepository, ProblemRepository
)

# Import models only for type hints
if TYPE_CHECKING:
    from ..models import Problem, ProblemSet, Course
    from purplex.submissions_app.models import PromptSubmission, SegmentationResult


class SubmissionService:
    """Service for managing submissions and related operations."""
    
    @staticmethod
    def create_submission(
        user: User,
        problem: 'Problem',
        prompt: str,
        problem_set: Optional['ProblemSet'] = None,
        course: Optional['Course'] = None,
        score: int = 0,
        test_results: Optional[Dict[str, Any]] = None,
        time_spent: Optional[timedelta] = None,
        code_variations: Optional[list] = None,
        passing_variations: int = 0,
        total_variations: int = 0,
        task_id: Optional[str] = None
    ) -> 'PromptSubmission':
        """
        Create a new submission record.
        
        Args:
            user: The user making the submission
            problem: The problem being submitted for
            prompt: The user's prompt or code
            problem_set: Optional problem set context
            course: Optional course context
            score: The submission score
            test_results: Test execution results
            time_spent: Time spent on the problem
            code_variations: List of generated code variations (EiPL)
            passing_variations: Number of variations that passed (EiPL)
            total_variations: Total number of variations (EiPL)
            task_id: Optional Celery task ID for tracking async processing
            
        Returns:
            The created PromptSubmission instance
        """
        return SubmissionRepository.create_submission(
            user=user,
            problem=problem,
            prompt=prompt,
            problem_set=problem_set,
            score=score,
            test_results=test_results,
            course=course,
            time_spent=time_spent,
            code_variations=code_variations,
            passing_variations=passing_variations,
            total_variations=total_variations,
            task_id=task_id
        )
    
    @staticmethod
    def get_problem_set_by_slug(slug: str) -> Optional['ProblemSet']:
        """
        Get a problem set by its slug.
        
        Args:
            slug: The problem set slug
            
        Returns:
            ProblemSet instance or None
        """
        return ProblemRepository.get_problem_set_by_slug(slug)
    
    @staticmethod
    def get_user_progress(
        user: User,
        problem: 'Problem',
        course: Optional['Course'] = None
    ) -> Optional[Any]:
        """
        Get user's progress for a specific problem.
        
        Args:
            user: The user
            problem: The problem
            course: Optional course context
            
        Returns:
            UserProgress instance or None
        """
        return ProgressRepository.get_user_progress(
            user=user,
            problem=problem,
            course=course
        )
    
    @staticmethod
    def verify_problem_in_set(problem: 'Problem', problem_set: 'ProblemSet') -> bool:
        """
        Verify if a problem belongs to a problem set.
        
        Args:
            problem: The problem to check
            problem_set: The problem set to check against
            
        Returns:
            True if the problem is in the set, False otherwise
        """
        return ProblemRepository.problem_in_set(problem, problem_set)
    
    @staticmethod
    def create_segmentation_result(
        submission: 'PromptSubmission',
        analysis: Dict[str, Any],
        segment_count: int,
        comprehension_level: str
    ) -> 'SegmentationResult':
        """
        Create a segmentation result for a submission.
        
        Args:
            submission: The submission to create segmentation for
            analysis: Analysis data (including segments and metadata)
            segment_count: Number of segments
            comprehension_level: Comprehension level ('relational' or 'multi_structural')
            
        Returns:
            Created SegmentationResult instance
        """
        return SubmissionRepository.create_segmentation_result(
            submission=submission,
            analysis=analysis,
            segment_count=segment_count,
            comprehension_level=comprehension_level
        )
