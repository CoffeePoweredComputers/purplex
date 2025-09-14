"""
Repository for ProblemSetMembership model data access.
"""

from typing import Optional, List, Dict, Any
from django.db.models import Q, Prefetch

from purplex.problems_app.models import ProblemSetMembership, Problem, ProblemSet
from .base_repository import BaseRepository


class ProblemSetMembershipRepository(BaseRepository):
    """
    Repository for all ProblemSetMembership-related database queries.
    
    This repository handles all data access for problem set memberships,
    managing the many-to-many relationship between problems and problem sets.
    """
    
    model_class = ProblemSetMembership
    
    @classmethod
    def create_membership(cls, problem_set: ProblemSet, problem: Problem, 
                         order: int = 0) -> ProblemSetMembership:
        """
        Create a new membership between a problem and a problem set.
        
        Args:
            problem_set: The problem set
            problem: The problem to add
            order: Order of the problem in the set
            
        Returns:
            Created ProblemSetMembership instance
        """
        return ProblemSetMembership.objects.create(
            problem_set=problem_set,
            problem=problem,
            order=order
        )
    
    @classmethod
    def get_problem_memberships(cls, problem: Problem) -> List[ProblemSetMembership]:
        """
        Get all problem set memberships for a specific problem.
        
        Args:
            problem: The problem to get memberships for
            
        Returns:
            List of ProblemSetMembership instances
        """
        return list(ProblemSetMembership.objects.filter(
            problem=problem
        ).select_related('problem_set'))
    
    @classmethod
    def get_problem_set_memberships(cls, problem_set: ProblemSet) -> List[ProblemSetMembership]:
        """
        Get all memberships for a specific problem set.
        
        Args:
            problem_set: The problem set to get memberships for
            
        Returns:
            List of ProblemSetMembership instances ordered by 'order'
        """
        return list(ProblemSetMembership.objects.filter(
            problem_set=problem_set
        ).select_related('problem').order_by('order'))
    
    @classmethod
    def get_problem_set_memberships_with_categories(cls, problem_set: ProblemSet) -> List[Dict[str, Any]]:
        """
        Get all memberships for a specific problem set with problem categories.
        
        Args:
            problem_set: The problem set to get memberships for
            
        Returns:
            List of dicts with membership and problem data including categories
        """
        memberships = ProblemSetMembership.objects.filter(
            problem_set=problem_set
        ).select_related('problem').prefetch_related(
            'problem__categories'
        ).order_by('order')
        
        result = []
        for membership in memberships:
            problem = membership.problem
            result.append({
                'order': membership.order,
                'problem': {
                    'id': problem.id,
                    'slug': problem.slug,
                    'title': problem.title,
                    'description': problem.description,
                    'difficulty': problem.difficulty,
                    'problem_type': problem.problem_type,
                    'segmentation_enabled': problem.segmentation_enabled,
                    'reference_solution': problem.reference_solution,
                    'is_active': problem.is_active,
                    'categories': [cat.name for cat in problem.categories.all()]
                }
            })
        
        return result
    
    @classmethod
    def count_problem_set_memberships(cls, problem_set: ProblemSet) -> int:
        """
        Count the number of memberships in a problem set.
        
        Args:
            problem_set: The problem set to count memberships for
            
        Returns:
            Number of memberships
        """
        return ProblemSetMembership.objects.filter(problem_set=problem_set).count()
    
    @classmethod
    def delete_problem_memberships(cls, problem: Problem) -> int:
        """
        Delete all problem set memberships for a problem.
        
        Args:
            problem: The problem whose memberships to delete
            
        Returns:
            Number of memberships deleted
        """
        deleted, _ = ProblemSetMembership.objects.filter(problem=problem).delete()
        return deleted
    
    @classmethod
    def delete_problem_set_memberships(cls, problem_set: ProblemSet) -> int:
        """
        Delete all memberships for a problem set.
        
        Args:
            problem_set: The problem set whose memberships to delete
            
        Returns:
            Number of memberships deleted
        """
        deleted, _ = ProblemSetMembership.objects.filter(problem_set=problem_set).delete()
        return deleted
    
    @classmethod
    def membership_exists(cls, problem_set: ProblemSet, problem: Problem) -> bool:
        """
        Check if a membership exists between a problem and problem set.
        
        Args:
            problem_set: The problem set
            problem: The problem
            
        Returns:
            True if membership exists, False otherwise
        """
        return ProblemSetMembership.objects.filter(
            problem_set=problem_set,
            problem=problem
        ).exists()
    
    @classmethod
    def get_membership(cls, problem_set: ProblemSet, problem: Problem) -> Optional[ProblemSetMembership]:
        """
        Get a specific membership between a problem and problem set.
        
        Args:
            problem_set: The problem set
            problem: The problem
            
        Returns:
            ProblemSetMembership instance or None
        """
        return ProblemSetMembership.objects.filter(
            problem_set=problem_set,
            problem=problem
        ).first()
    
    @classmethod
    def update_membership_order(cls, problem_set: ProblemSet, problem: Problem, 
                               new_order: int) -> bool:
        """
        Update the order of a problem in a problem set.
        
        Args:
            problem_set: The problem set
            problem: The problem
            new_order: The new order value
            
        Returns:
            True if updated, False if not found
        """
        updated = ProblemSetMembership.objects.filter(
            problem_set=problem_set,
            problem=problem
        ).update(order=new_order)
        return updated > 0
    
    @classmethod
    def bulk_create_memberships(cls, memberships: List[Dict[str, Any]]) -> List[ProblemSetMembership]:
        """
        Bulk create multiple memberships.
        
        Args:
            memberships: List of dicts with problem_set, problem, and order
            
        Returns:
            List of created ProblemSetMembership instances
        """
        membership_objects = [
            ProblemSetMembership(
                problem_set=m['problem_set'],
                problem=m['problem'],
                order=m.get('order', 0)
            )
            for m in memberships
        ]
        return list(ProblemSetMembership.objects.bulk_create(
            membership_objects,
            ignore_conflicts=True
        ))