"""Admin-specific service layer for problem management."""
import logging
from typing import Dict, List, Any, Optional, Tuple
from django.db import transaction
from django.core.exceptions import ValidationError

from ..models import (
    Problem, ProblemCategory, ProblemSet, 
    ProblemSetMembership, TestCase
)

logger = logging.getLogger(__name__)


class AdminProblemService:
    """Handle all admin-specific problem management business logic."""
    
    @staticmethod
    def handle_category_transformation(data: dict) -> dict:
        """
        Transform category string to category_ids array, creating category if needed.
        
        Args:
            data: Request data dictionary
            
        Returns:
            Modified data dictionary with category_ids
        """
        if 'category' in data and data['category']:
            category_name = data.pop('category')
            try:
                category = ProblemCategory.objects.get(name__iexact=category_name)
                data['category_ids'] = [category.id]
            except ProblemCategory.DoesNotExist:
                # Create a new category if it doesn't exist
                with transaction.atomic():
                    category = ProblemCategory.objects.create(
                        name=category_name,
                        description=f"Category for {category_name} problems"
                    )
                    data['category_ids'] = [category.id]
        return data
    
    @staticmethod
    def set_eipl_defaults(data: dict) -> dict:
        """
        Set default values for EiPL problem type.
        
        Args:
            data: Request data dictionary
            
        Returns:
            Modified data dictionary with EiPL defaults
        """
        if data.get('problem_type') == 'eipl':
            # For EiPL, we need to provide default values for required function fields
            if not data.get('function_name'):
                data['function_name'] = 'explain_code'
            if not data.get('function_signature'):
                data['function_signature'] = 'def explain_code():'
        return data
    
    @staticmethod
    @transaction.atomic
    def create_problem_with_relations(
        problem: Problem, 
        problem_set_slugs: List[str]
    ) -> Tuple[int, List[str]]:
        """
        Create problem set memberships for a problem.
        
        Args:
            problem: Problem instance
            problem_set_slugs: List of problem set slugs
            
        Returns:
            Tuple of (added_count, missing_slugs)
        """
        added_count = 0
        missing_slugs = []
        
        for slug in problem_set_slugs:
            try:
                problem_set = ProblemSet.objects.get(slug=slug)
                ProblemSetMembership.objects.create(
                    problem_set=problem_set,
                    problem=problem,
                    order=problem_set.problems.count()
                )
                added_count += 1
            except ProblemSet.DoesNotExist:
                logger.warning(f"Problem set with slug '{slug}' not found during problem creation")
                missing_slugs.append(slug)
        
        return added_count, missing_slugs
    
    @staticmethod
    def prepare_problem_data(request_data: dict) -> Tuple[dict, List[str]]:
        """
        Prepare problem data for creation/update.
        
        Args:
            request_data: Raw request data
            
        Returns:
            Tuple of (processed_data, problem_set_slugs)
        """
        data = request_data.copy() if hasattr(request_data, 'copy') else dict(request_data)
        
        # Handle category transformation
        data = AdminProblemService.handle_category_transformation(data)
        
        # Extract problem sets for later processing
        problem_set_slugs = data.pop('problem_sets', [])
        
        # Set EiPL defaults if needed
        data = AdminProblemService.set_eipl_defaults(data)
        
        return data, problem_set_slugs
    
    @staticmethod
    @transaction.atomic
    def update_problem_sets(
        problem: Problem, 
        problem_set_slugs: List[str]
    ) -> Tuple[int, List[str]]:
        """
        Update problem set memberships for a problem.
        
        Args:
            problem: Problem instance
            problem_set_slugs: List of problem set slugs
            
        Returns:
            Tuple of (updated_count, missing_slugs)
        """
        # Clear existing memberships
        ProblemSetMembership.objects.filter(problem=problem).delete()
        
        # Add new memberships
        return AdminProblemService.create_problem_with_relations(problem, problem_set_slugs)
    
    @staticmethod
    def validate_problem_set_title(title: str, current_slug: Optional[str] = None) -> Optional[str]:
        """
        Check if a problem set title would create a duplicate slug.
        
        Args:
            title: Problem set title
            current_slug: Current slug (for updates)
            
        Returns:
            Error message if duplicate, None otherwise
        """
        from django.utils.text import slugify
        
        potential_slug = slugify(title)
        
        # Check if another problem set already has this slug
        if current_slug and potential_slug != current_slug:
            if ProblemSet.objects.filter(slug=potential_slug).exists():
                return f'A problem set with similar title already exists (slug: {potential_slug})'
        elif not current_slug and ProblemSet.objects.filter(slug=potential_slug).exists():
            return f'A problem set with similar title already exists (slug: {potential_slug})'
        
        return None
    
    @staticmethod
    @transaction.atomic
    def create_problem_set_with_problems(
        problem_set: ProblemSet,
        problem_slugs: List[str]
    ) -> Dict[str, Any]:
        """
        Create problem set with problem memberships.
        
        Args:
            problem_set: ProblemSet instance
            problem_slugs: List of problem slugs to add
            
        Returns:
            Dictionary with results
        """
        import json
        
        # Parse JSON string if needed
        if isinstance(problem_slugs, str):
            try:
                problem_slugs = json.loads(problem_slugs)
            except json.JSONDecodeError:
                raise ValidationError('Invalid problem_slugs format - must be a JSON array')
        
        # Validate that problem_slugs is a list
        if not isinstance(problem_slugs, list):
            raise ValidationError('problem_slugs must be an array')
        
        # Collect results
        missing_problems = []
        added_problems = []
        
        for order, slug in enumerate(problem_slugs):
            try:
                problem = Problem.objects.get(slug=slug)
                ProblemSetMembership.objects.create(
                    problem_set=problem_set,
                    problem=problem,
                    order=order
                )
                added_problems.append(slug)
            except Problem.DoesNotExist:
                missing_problems.append(slug)
        
        # Report if some problems were not found
        if missing_problems:
            logger.warning(f"Problem set created but some problems not found: {missing_problems}")
        
        return {
            'problems_added': len(added_problems),
            'missing_problems': missing_problems
        }
    
    @staticmethod
    @transaction.atomic
    def update_problem_set_with_problems(
        problem_set: ProblemSet,
        problem_slugs: Optional[List[str]]
    ) -> Dict[str, Any]:
        """
        Update problem set with new problem memberships.
        
        Args:
            problem_set: ProblemSet instance
            problem_slugs: List of problem slugs to set (None to skip)
            
        Returns:
            Dictionary with results
        """
        import json
        
        if problem_slugs is None:
            return {}
        
        # Parse JSON string if needed
        if isinstance(problem_slugs, str):
            try:
                problem_slugs = json.loads(problem_slugs)
            except json.JSONDecodeError:
                raise ValidationError('Invalid problem_slugs format - must be a JSON array')
        
        # Validate that problem_slugs is a list
        if not isinstance(problem_slugs, list):
            raise ValidationError('problem_slugs must be an array')
        
        # Clear existing memberships
        ProblemSetMembership.objects.filter(problem_set=problem_set).delete()
        
        # Collect results
        missing_problems = []
        added_problems = []
        
        # Add new memberships
        for order, slug in enumerate(problem_slugs):
            try:
                problem = Problem.objects.get(slug=slug)
                ProblemSetMembership.objects.create(
                    problem_set=problem_set,
                    problem=problem,
                    order=order
                )
                added_problems.append(slug)
            except Problem.DoesNotExist:
                missing_problems.append(slug)
        
        # Report if some problems were not found
        if missing_problems:
            logger.warning(f"Problem set updated but some problems not found: {missing_problems}")
        
        return {
            'problems_updated': len(added_problems),
            'missing_problems': missing_problems
        }