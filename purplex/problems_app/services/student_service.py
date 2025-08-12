"""Service layer for student-related business logic."""

import logging
from typing import List, Optional
from django.db.models import Count, QuerySet
from django.shortcuts import get_object_or_404

from ..models import Problem, ProblemSet, ProblemCategory

logger = logging.getLogger(__name__)


class StudentService:
    """Handle all student-related business logic."""
    
    @staticmethod
    def get_active_problems(user=None) -> QuerySet:
        """
        Get all active problems visible to students.
        
        Args:
            user: Optional user for filtering (future use)
            
        Returns:
            QuerySet of active problems with optimized queries
        """
        return Problem.objects.filter(is_active=True).select_related(
            'created_by'
        ).prefetch_related(
            'categories',
            'test_cases',
            'problem_sets'
        ).only(
            'slug', 'title', 'description', 'difficulty', 'problem_type', 
            'function_name', 'tags', 'is_active', 'created_at', 'created_by_id'
        )
    
    @staticmethod
    def get_problem_detail(slug: str) -> Problem:
        """
        Get detailed problem information for students.
        
        Args:
            slug: Problem slug
            
        Returns:
            Problem instance
            
        Raises:
            Http404: If problem not found or not active
        """
        return get_object_or_404(Problem, slug=slug, is_active=True)
    
    @staticmethod
    def get_visible_test_cases(problem: Problem) -> QuerySet:
        """
        Get only non-hidden test cases for a problem.
        
        Args:
            problem: Problem instance
            
        Returns:
            QuerySet of visible test cases
        """
        return problem.test_cases.filter(is_hidden=False)
    
    @staticmethod
    def get_public_problem_sets() -> QuerySet:
        """
        Get all public problem sets with optimized queries.
        
        Returns:
            QuerySet of public problem sets
        """
        return ProblemSet.objects.filter(is_public=True).prefetch_related(
            'problems',
            'problems__categories'
        ).order_by('-created_at')
    
    @staticmethod
    def get_problem_set_detail(slug: str) -> ProblemSet:
        """
        Get detailed problem set information.
        
        Args:
            slug: Problem set slug
            
        Returns:
            ProblemSet instance with related data
            
        Raises:
            Http404: If problem set not found or not public
        """
        return get_object_or_404(
            ProblemSet.objects.prefetch_related(
                'problems',
                'problems__categories',
                'problems__test_cases'
            ),
            slug=slug,
            is_public=True
        )
    
    @staticmethod
    def get_problem_set_problems(problem_set: ProblemSet, user=None) -> List[dict]:
        """
        Get ordered problems for a problem set.
        
        Args:
            problem_set: ProblemSet instance
            user: Optional user for progress filtering
            
        Returns:
            List of problem data with ordering
        """
        # Get problems through the membership table to preserve order
        memberships = problem_set.problemsetmembership_set.select_related(
            'problem'
        ).prefetch_related(
            'problem__categories',
            'problem__test_cases'
        ).order_by('order')
        
        problems_data = []
        for membership in memberships:
            problem = membership.problem
            if problem.is_active:
                problem_data = {
                    'slug': problem.slug,
                    'title': problem.title,
                    'description': problem.description,
                    'difficulty': problem.difficulty,
                    'problem_type': problem.problem_type,
                    'order': membership.order,
                    'categories': [cat.name for cat in problem.categories.all()],
                    'test_case_count': problem.test_cases.count(),
                    'visible_test_case_count': problem.test_cases.filter(is_hidden=False).count()
                }
                problems_data.append(problem_data)
        
        return problems_data
    
    @staticmethod
    def get_all_categories() -> QuerySet:
        """
        Get all problem categories ordered by their display order.
        
        Returns:
            QuerySet of ProblemCategory instances
        """
        return ProblemCategory.objects.all().order_by('order', 'name')