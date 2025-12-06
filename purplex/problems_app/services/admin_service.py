"""Admin-specific service layer for problem management."""
import logging
from typing import Dict, List, Any, Optional, Tuple, TYPE_CHECKING
from django.core.exceptions import ValidationError

from ..repositories import (
    ProblemRepository,
    ProblemSetMembershipRepository,
    ProblemCategoryRepository,
    TestCaseRepository,
    ProblemSetRepository
)

# Import models only for type hints
if TYPE_CHECKING:
    from ..models import (
        Problem, ProblemCategory, ProblemSet, 
        TestCase
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
            # Use repository to find exact category match
            category = ProblemRepository.find_category_by_exact_name(category_name)
            
            if category:
                data['category_ids'] = [category.id]
            else:
                # Create a new category if it doesn't exist
                category = ProblemRepository.create_category(
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
    def create_problem_with_relations(
        problem: 'Problem', 
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
            problem_set = ProblemRepository.get_problem_set_by_slug(slug)
            if problem_set:
                # Get the count of problems in the set for ordering
                order = ProblemSetMembershipRepository.count_problem_set_memberships(problem_set)
                ProblemSetMembershipRepository.create_membership(
                    problem_set=problem_set,
                    problem=problem,
                    order=order
                )
                added_count += 1
            else:
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
    def get_all_problem_sets() -> List:
        """
        Get all problem sets for admin view.
        
        Returns:
            List of all problem sets with related data
        """
        return ProblemRepository.get_all_problem_sets()
    
    @staticmethod
    def get_all_categories() -> List[Dict[str, Any]]:
        """
        Get all problem categories for admin view.
        
        Returns:
            List of category dictionaries
        """
        return ProblemRepository.get_all_categories()
    
    @staticmethod
    def get_problem_sets_by_slugs(slugs: List[str]) -> List:
        """
        Get problem sets by their slugs.
        
        Args:
            slugs: List of problem set slugs
            
        Returns:
            List of matching problem sets
        """
        if not slugs:
            return []
        
        # Get each problem set by slug
        problem_sets = []
        for slug in slugs:
            problem_set = ProblemRepository.get_problem_set_by_slug(slug)
            if problem_set:
                problem_sets.append(problem_set)
        
        return problem_sets
    
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
            if ProblemRepository.get_problem_set_by_slug(potential_slug) is not None:
                return f'A problem set with similar title already exists (slug: {potential_slug})'
        elif not current_slug and ProblemRepository.get_problem_set_by_slug(potential_slug) is not None:
            return f'A problem set with similar title already exists (slug: {potential_slug})'
        
        return None
    
    @staticmethod
    def create_problem_set_with_problems(
        problem_set: 'ProblemSet',
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
            problem = ProblemRepository.get_problem_by_slug(slug)
            if problem:
                ProblemSetMembershipRepository.create_membership(
                    problem_set=problem_set,
                    problem=problem,
                    order=order
                )
                added_problems.append(slug)
            else:
                missing_problems.append(slug)
        
        # Report if some problems were not found
        if missing_problems:
            logger.warning(f"Problem set created but some problems not found: {missing_problems}")
        
        return {
            'problems_added': len(added_problems),
            'missing_problems': missing_problems
        }
    
    @staticmethod
    def update_problem_set_with_problems(
        problem_set: 'ProblemSet',
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
        ProblemSetMembershipRepository.delete_problem_set_memberships(problem_set)
        
        # Collect results
        missing_problems = []
        added_problems = []
        
        # Add new memberships
        for order, slug in enumerate(problem_slugs):
            problem = ProblemRepository.get_problem_by_slug(slug)
            if problem:
                ProblemSetMembershipRepository.create_membership(
                    problem_set=problem_set,
                    problem=problem,
                    order=order
                )
                added_problems.append(slug)
            else:
                missing_problems.append(slug)
        
        # Report if some problems were not found
        if missing_problems:
            logger.warning(f"Problem set updated but some problems not found: {missing_problems}")
        
        return {
            'problems_updated': len(added_problems),
            'missing_problems': missing_problems
        }
    
    @staticmethod
    def get_all_problems_optimized() -> List:
        """
        Get all problems with optimized queries for admin interface.
        
        Returns:
            List with select_related and prefetch_related optimizations
        """
        return ProblemRepository.get_all_problems()
    
    @staticmethod
    def get_problem_by_slug(slug: str) -> Optional['Problem']:
        """
        Get a problem by slug.
        
        Args:
            slug: Problem slug
            
        Returns:
            Problem instance or None
        """
        return ProblemRepository.get_problem_by_slug(slug)
    
    @staticmethod
    def get_problem_set_by_slug(slug: str) -> Optional['ProblemSet']:
        """
        Get a problem set by slug.
        
        Args:
            slug: Problem set slug
            
        Returns:
            ProblemSet instance or None
        """
        return ProblemRepository.get_problem_set_by_slug(slug)
    
    @staticmethod
    def create_problem(validated_data: dict) -> 'Problem':
        """
        Create a new problem using repository.
        
        Args:
            validated_data: Validated problem data
            
        Returns:
            Created Problem instance
        """
        return ProblemRepository.create(**validated_data)
    
    @staticmethod
    def update_problem(instance: 'Problem', validated_data: dict) -> 'Problem':
        """
        Update an existing problem.
        
        Args:
            instance: Problem instance to update
            validated_data: Validated data for update
            
        Returns:
            Updated Problem instance
        """
        return ProblemRepository.update_problem(instance, **validated_data)
    
    @staticmethod
    def get_categories_by_ids(category_ids: List[int]) -> List['ProblemCategory']:
        """
        Get categories by their IDs.

        Args:
            category_ids: List of category IDs

        Returns:
            List of ProblemCategory model instances
        """
        return ProblemCategoryRepository.get_categories_by_ids(category_ids)
    
    @staticmethod
    def create_test_case(problem: 'Problem', test_case_data: dict) -> 'TestCase':
        """
        Create a test case for a problem.
        
        Args:
            problem: Problem instance
            test_case_data: Test case data
            
        Returns:
            Created TestCase instance
        """
        return TestCaseRepository.create(problem=problem, **test_case_data)
    
    @staticmethod
    def create_course(validated_data: dict) -> 'Course':
        """
        Create a new course using repository.
        
        Args:
            validated_data: Validated course data
            
        Returns:
            Created Course instance
        """
        from ..repositories import CourseRepository
        return CourseRepository.create(**validated_data)
    
    @staticmethod
    def get_problem_set_by_id(problem_set_id: int) -> Optional['ProblemSet']:
        """
        Get a problem set by ID.
        
        Args:
            problem_set_id: Problem set ID
            
        Returns:
            ProblemSet instance or None
        """
        return ProblemSetRepository.get_by_id(problem_set_id)
    
    @staticmethod
    def create_course_problem_set(course: 'Course', problem_set: 'ProblemSet', order: int = 0) -> 'CourseProblemSet':
        """
        Create a course-problem set relationship.
        
        Args:
            course: Course instance
            problem_set: ProblemSet instance
            order: Order in the course
            
        Returns:
            Created CourseProblemSet instance
        """
        from ..repositories import CourseProblemSetRepository
        return CourseProblemSetRepository.create(
            course=course,
            problem_set=problem_set,
            order=order
        )
    
    @staticmethod
    def check_course_exists(course_id: str) -> bool:
        """
        Check if a course with the given course_id exists.
        
        Args:
            course_id: Course ID to check
            
        Returns:
            True if course exists, False otherwise
        """
        from ..repositories import CourseRepository
        return CourseRepository.course_exists(course_id)
    
    @staticmethod
    def get_test_case(test_case_id: int, problem_slug: str) -> Optional['TestCase']:
        """
        Get a test case by ID and problem slug.
        
        Args:
            test_case_id: Test case ID
            problem_slug: Problem slug for validation
            
        Returns:
            TestCase instance or None
        """
        problem = ProblemRepository.get_problem_by_slug(problem_slug)
        if not problem:
            return None
        
        # Get the test case and verify it belongs to the problem
        return ProblemRepository.get_problem_test_case_by_id(problem, test_case_id, include_hidden=True)
    
    @staticmethod
    def delete_problem(problem: 'Problem') -> dict:
        """
        Delete a problem.
        
        Args:
            problem: Problem instance to delete
            
        Returns:
            Dict with 'success' bool and optional 'error' message
        """
        from purplex.submissions.repositories import SubmissionRepository

        # Check for existing submissions
        submission_count = SubmissionRepository.count_for_problem(problem)
        if submission_count > 0:
            return {
                'success': False,
                'error': f'This problem has {submission_count} student submission(s). To preserve academic records, problems with submissions cannot be deleted. You can deactivate the problem instead to hide it from students.'
            }
        
        try:
            problem.delete()
            return {'success': True}
        except Exception as e:
            logger.error(f"Failed to delete problem {problem.slug}: {str(e)}")
            return {'success': False, 'error': f'Failed to delete problem: {str(e)}'}
    
    @staticmethod
    def delete_problem_set(problem_set: 'ProblemSet') -> bool:
        """
        Delete a problem set.
        
        Args:
            problem_set: ProblemSet instance to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            problem_set.delete()
            return True
        except Exception as e:
            logger.error(f"Failed to delete problem set {problem_set.slug}: {str(e)}")
            return False
    
    @staticmethod
    def delete_test_case(test_case_id: int) -> bool:
        """
        Delete a test case by ID.
        
        Args:
            test_case_id: Test case ID to delete
            
        Returns:
            True if deleted successfully
        """
        return TestCaseRepository.delete_test_case(test_case_id)
    
    @staticmethod
    def update_problem_set_relations(
        problem: 'Problem',
        problem_sets: List['ProblemSet']
    ) -> None:
        """
        Update problem set relationships for a problem.

        Args:
            problem: Problem instance
            problem_sets: List of ProblemSet instances to associate
        """
        # Clear existing memberships for this problem
        ProblemSetMembershipRepository.delete_problem_memberships(problem)

        # Create new memberships with proper ordering
        for problem_set in problem_sets:
            # Get the current count of problems in the set for ordering
            order = ProblemSetMembershipRepository.count_problem_set_memberships(problem_set)
            ProblemSetMembershipRepository.create_membership(
                problem_set=problem_set,
                problem=problem,
                order=order
            )