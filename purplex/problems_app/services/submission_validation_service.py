"""Submission validation service for centralizing submission validation logic."""
from typing import Optional, Tuple
from ..models import Problem, ProblemSet, Course
from .validation_service import ProblemValidationService


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
        try:
            problem = Problem.objects.get(slug=problem_slug, is_active=True)
            validated_data['problem'] = problem
        except Problem.DoesNotExist:
            return False, 'Problem not found', None
        
        # Validate optional problem set
        if problem_set_slug:
            try:
                problem_set = ProblemSet.objects.get(slug=problem_set_slug)
                validated_data['problem_set'] = problem_set
            except ProblemSet.DoesNotExist:
                return False, 'Problem set not found', None
        
        # Validate optional course
        if course_id:
            try:
                course = Course.objects.get(course_id=course_id, is_active=True, is_deleted=False)
                validated_data['course'] = course
            except (Course.DoesNotExist, ValueError):
                return False, 'Course not found', None
        
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
        try:
            problem = Problem.objects.get(slug=problem_slug, is_active=True)
            validated_data['problem'] = problem
        except Problem.DoesNotExist:
            return False, 'Problem not found', None
        
        # Validate optional problem set
        if problem_set_slug:
            try:
                problem_set = ProblemSet.objects.get(slug=problem_set_slug)
                validated_data['problem_set'] = problem_set
            except ProblemSet.DoesNotExist:
                return False, 'Problem set not found', None
        
        # Validate optional course
        if course_id:
            try:
                course = Course.objects.get(course_id=course_id, is_active=True, is_deleted=False)
                validated_data['course'] = course
            except (Course.DoesNotExist, ValueError):
                return False, 'Course not found', None
        
        validated_data['user_code'] = user_code.strip()
        return True, None, validated_data