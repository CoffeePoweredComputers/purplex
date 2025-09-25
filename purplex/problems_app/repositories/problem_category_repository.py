"""
Repository for ProblemCategory model data access.
"""

from typing import Optional, List, Dict, Any
from django.db.models import Count

from purplex.problems_app.models import ProblemCategory
from .base_repository import BaseRepository


class ProblemCategoryRepository(BaseRepository):
    """
    Repository for all ProblemCategory-related database queries.
    
    This repository handles all data access for problem categories,
    including retrieval, creation, and management of categories.
    """
    
    model_class = ProblemCategory
    
    @classmethod
    def get_all_categories(cls) -> List:
        """
        Get all problem categories ordered by order and name.
        
        Returns:
            QuerySet of all problem categories
        """
        return list(ProblemCategory.objects.all().order_by('order', 'name'))
    
    @classmethod
    def get_category_by_slug(cls, slug: str) -> Optional[ProblemCategory]:
        """
        Get a category by its slug.
        
        Args:
            slug: The category slug
            
        Returns:
            ProblemCategory instance or None
        """
        return ProblemCategory.objects.filter(slug=slug).first()
    
    @classmethod
    def get_category_by_name(cls, name: str) -> Optional[ProblemCategory]:
        """
        Get a category by its name.
        
        Args:
            name: The category name
            
        Returns:
            ProblemCategory instance or None
        """
        return ProblemCategory.objects.filter(name=name).first()
    
    @classmethod
    def create_category(cls, name: str, description: str, **kwargs) -> ProblemCategory:
        """
        Create a new problem category.
        
        Args:
            name: Category name
            description: Category description
            **kwargs: Additional fields (slug, icon, color, order)
            
        Returns:
            Created ProblemCategory instance
        """
        return ProblemCategory.objects.create(
            name=name,
            description=description,
            **kwargs
        )
    
    @classmethod
    def get_categories_with_problem_count(cls) -> List:
        """
        Get all categories annotated with the number of problems in each.
        
        Returns:
            QuerySet of categories with problem_count annotation
        """
        return list(ProblemCategory.objects.annotate(
            problem_count=Count('problem')
        ).order_by('order', 'name'))
    
    @classmethod
    def update_category(cls, category_id: int, **kwargs) -> bool:
        """
        Update a category by ID.
        
        Args:
            category_id: The category ID
            **kwargs: Fields to update
            
        Returns:
            True if updated, False if not found
        """
        updated = ProblemCategory.objects.filter(id=category_id).update(**kwargs)
        return updated > 0
    
    @classmethod
    def update_category_order(cls, category_id: int, new_order: int) -> bool:
        """
        Update the display order of a category.
        
        Args:
            category_id: The category ID
            new_order: The new order value
            
        Returns:
            True if updated, False if not found
        """
        updated = ProblemCategory.objects.filter(id=category_id).update(order=new_order)
        return updated > 0
    
    @classmethod
    def get_categories_by_ids(cls, category_ids: List[int]) -> List[ProblemCategory]:
        """
        Get categories by their IDs.

        Args:
            category_ids: List of category IDs

        Returns:
            List of ProblemCategory model instances
        """
        return list(ProblemCategory.objects.filter(id__in=category_ids))
    
    @classmethod
    def delete_category(cls, category_id: int) -> bool:
        """
        Delete a category by ID.
        
        Args:
            category_id: The category ID
            
        Returns:
            True if deleted, False if not found
        """
        deleted, _ = ProblemCategory.objects.filter(id=category_id).delete()
        return deleted > 0
    
    @classmethod
    def category_exists(cls, name: str) -> bool:
        """
        Check if a category with the given name exists.
        
        Args:
            name: The category name
            
        Returns:
            True if exists, False otherwise
        """
        return ProblemCategory.objects.filter(name=name).exists()
    
    @classmethod
    def search_categories(cls, query: str) -> List:
        """
        Search categories by name or description.
        
        Args:
            query: Search query string
            
        Returns:
            QuerySet of matching categories
        """
        from django.db.models import Q
        
        return list(ProblemCategory.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        ).order_by('order', 'name'))
    
    @classmethod
    def get_active_categories(cls) -> List:
        """
        Get categories that have at least one problem.
        
        Returns:
            QuerySet of categories with problems
        """
        return list(ProblemCategory.objects.annotate(
            problem_count=Count('problem')
        ).filter(problem_count__gt=0).order_by('order', 'name'))