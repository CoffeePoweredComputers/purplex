"""Submission validation service for centralizing submission validation logic."""
from typing import Optional, Tuple, TYPE_CHECKING
from ..repositories import ProblemRepository, CourseRepository
from .validation_service import ProblemValidationService

# Import models only for type hints
if TYPE_CHECKING:
    from ..models import Problem, ProblemSet, Course


class SubmissionValidationService:
    """Service for validating submission requests"""
    
    @staticmethod
    def validate_eipl_submission(data: dict) -> Tuple[bool, Optional[str], Optional[dict]]:
        """
        Validate EiPL submission request data
        
        Args:
            data: Request data dictionary
            
        Returns:
            Tuple[bool, Optional[str], Optional[dict]]: 
            (is_valid, error_message, validated_data)
        """
        validated_data = {}
        
        # Extract required fields
        problem_slug = data.get('problem_slug')
        user_prompt = data.get('user_prompt', '')
        problem_set_slug = data.get('problem_set_slug')
        course_id = data.get('course_id')
        
        # Validate required problem_slug
        if not problem_slug:
            return False, 'problem_slug is required', None
        
        # Validate user prompt
        is_valid, error = ProblemValidationService.validate_user_prompt(user_prompt)
        if not is_valid:
            return False, error, None
        
        # Validate problem exists and is active
        problem = ProblemRepository.get_problem_by_slug(problem_slug)
        if not problem or not problem.is_active:
            return False, 'Problem not found', None
        validated_data['problem'] = problem
        
        # Validate optional problem set
        if problem_set_slug:
            problem_set = ProblemRepository.get_problem_set_by_slug(problem_set_slug)
            if not problem_set:
                return False, 'Problem set not found', None
            validated_data['problem_set'] = problem_set
        
        # Validate optional course
        if course_id:
            course = CourseRepository.get_active_course(course_id)
            if not course:
                return False, 'Course not found', None
            validated_data['course'] = course
        
        validated_data['user_prompt'] = user_prompt.strip()
        return True, None, validated_data
    
    @staticmethod
    def validate_code_submission(data: dict) -> Tuple[bool, Optional[str], Optional[dict]]:
        """
        Validate code submission request data
        
        Args:
            data: Request data dictionary
            
        Returns:
            Tuple[bool, Optional[str], Optional[dict]]: 
            (is_valid, error_message, validated_data)
        """
        validated_data = {}
        
        # Extract required fields
        problem_slug = data.get('problem_slug')
        user_code = data.get('user_code', '')
        problem_set_slug = data.get('problem_set_slug')
        course_id = data.get('course_id')
        
        # Validate required problem_slug
        if not problem_slug:
            return False, 'problem_slug is required', None
        
        # Validate user code
        is_valid, error = ProblemValidationService.validate_user_code(user_code)
        if not is_valid:
            return False, error, None
        
        # Validate problem exists and is active
        problem = ProblemRepository.get_problem_by_slug(problem_slug)
        if not problem or not problem.is_active:
            return False, 'Problem not found', None
        validated_data['problem'] = problem
        
        # Validate optional problem set
        if problem_set_slug:
            problem_set = ProblemRepository.get_problem_set_by_slug(problem_set_slug)
            if not problem_set:
                return False, 'Problem set not found', None
            validated_data['problem_set'] = problem_set
        
        # Validate optional course
        if course_id:
            course = CourseRepository.get_active_course(course_id)
            if not course:
                return False, 'Course not found', None
            validated_data['course'] = course
        
        validated_data['user_code'] = user_code.strip()
        return True, None, validated_data