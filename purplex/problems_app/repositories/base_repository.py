"""
Base repository class with common database patterns.
"""

from typing import Optional, List, Dict, Any, Type, TypeVar, Generic, Tuple
from django.db.models import Model, QuerySet
from django.core.paginator import Paginator

# Type variable for the model class
T = TypeVar('T', bound=Model)


class BaseRepository(Generic[T]):
    """
    Base repository with common database operations.
    
    All repositories should inherit from this class to ensure
    consistent data access patterns.
    
    IMPORTANT: All public methods return domain objects (Model instances) or
    Python data types (list, dict, etc), NEVER QuerySets.
    
    Services should NEVER import django.db.models or perform ORM operations.
    All database logic must be encapsulated in repositories.
    """
    
    model_class: Optional[Type[T]] = None
    
    @classmethod
    def get_by_id(cls, id: int) -> Optional[T]:
        """Get a single record by primary key."""
        if not cls.model_class:
            raise NotImplementedError("model_class must be defined")
        
        try:
            return cls.model_class.objects.get(pk=id)
        except cls.model_class.DoesNotExist:
            return None
    
    @classmethod
    def get_all(cls) -> List[T]:
        """Get all records as a list.
        
        WARNING: This loads all records into memory.
        For large datasets, use paginate() or create specific filtered methods.
        """
        if not cls.model_class:
            raise NotImplementedError("model_class must be defined")
        
        return list(cls.model_class.objects.all())
    
    @classmethod
    def filter(cls, **kwargs) -> List[T]:
        """Filter records by given criteria and return as list.
        
        For complex queries with optimizations, create specific methods
        that include select_related/prefetch_related.
        """
        if not cls.model_class:
            raise NotImplementedError("model_class must be defined")
        
        return list(cls.model_class.objects.filter(**kwargs))
    
    @classmethod
    def exists(cls, **kwargs) -> bool:
        """Check if records exist matching criteria."""
        if not cls.model_class:
            raise NotImplementedError("model_class must be defined")
        
        return cls.model_class.objects.filter(**kwargs).exists()
    
    @classmethod
    def count(cls, **kwargs) -> int:
        """Count records matching criteria."""
        if not cls.model_class:
            raise NotImplementedError("model_class must be defined")
        
        return cls.model_class.objects.filter(**kwargs).count()
    
    @classmethod
    def create(cls, **kwargs) -> T:
        """Create a new record."""
        if not cls.model_class:
            raise NotImplementedError("model_class must be defined")
        
        return cls.model_class.objects.create(**kwargs)
    
    @classmethod
    def update_or_create(cls, defaults: Dict[str, Any], **kwargs) -> tuple[T, bool]:
        """Update existing or create new record."""
        if not cls.model_class:
            raise NotImplementedError("model_class must be defined")
        
        return cls.model_class.objects.update_or_create(defaults=defaults, **kwargs)
    
    @classmethod
    def bulk_create(cls, objects: List[T], **kwargs) -> List[T]:
        """Bulk create records."""
        if not cls.model_class:
            raise NotImplementedError("model_class must be defined")
        
        return list(cls.model_class.objects.bulk_create(objects, **kwargs))
    
    @classmethod
    def delete(cls, **kwargs) -> Tuple[int, Dict[str, int]]:
        """Delete records matching criteria."""
        if not cls.model_class:
            raise NotImplementedError("model_class must be defined")
        
        return cls.model_class.objects.filter(**kwargs).delete()
    
    @classmethod
    def filter_with_select_related(cls, select_fields: List[str], **kwargs) -> List[T]:
        """Filter with select_related optimization and return as list."""
        if not cls.model_class:
            raise NotImplementedError("model_class must be defined")
        
        queryset = cls.model_class.objects.filter(**kwargs)
        if select_fields:
            queryset = queryset.select_related(*select_fields)
        return list(queryset)
    
    @classmethod
    def filter_with_prefetch(cls, prefetch_fields: List[str], **kwargs) -> List[T]:
        """Filter with prefetch_related optimization and return as list."""
        if not cls.model_class:
            raise NotImplementedError("model_class must be defined")
        
        queryset = cls.model_class.objects.filter(**kwargs)
        if prefetch_fields:
            queryset = queryset.prefetch_related(*prefetch_fields)
        return list(queryset)
    
    @classmethod
    def get_first(cls, **kwargs) -> Optional[T]:
        """Get the first record matching criteria."""
        if not cls.model_class:
            raise NotImplementedError("model_class must be defined")
        
        return cls.model_class.objects.filter(**kwargs).first()
    
    @classmethod
    def get_last(cls, **kwargs) -> Optional[T]:
        """Get the last record matching criteria."""
        if not cls.model_class:
            raise NotImplementedError("model_class must be defined")
        
        return cls.model_class.objects.filter(**kwargs).last()
    
    @classmethod
    def paginate(cls, page: int = 1, per_page: int = 20, order_by: str = '-id', **filters) -> Dict[str, Any]:
        """Return paginated results as dict with items list.
        
        Returns:
            Dict with keys:
            - items: List of model instances
            - total: Total count
            - page: Current page
            - per_page: Items per page
            - has_next: Boolean
            - has_prev: Boolean
            - total_pages: Total number of pages
        """
        if not cls.model_class:
            raise NotImplementedError("model_class must be defined")
        
        queryset = cls.model_class.objects.filter(**filters).order_by(order_by)
        paginator = Paginator(queryset, per_page)
        
        page_obj = paginator.get_page(page)
        
        return {
            'items': list(page_obj.object_list),
            'total': paginator.count,
            'page': page,
            'per_page': per_page,
            'has_next': page_obj.has_next(),
            'has_prev': page_obj.has_previous(),
            'total_pages': paginator.num_pages
        }
    
    # Protected methods for internal repository use only
    @classmethod
    def _get_queryset(cls, **kwargs) -> QuerySet:
        """INTERNAL USE ONLY: Get queryset for complex operations within repository.
        
        This method should NEVER be called from services.
        Use it only within repository methods to build complex queries.
        """
        if not cls.model_class:
            raise NotImplementedError("model_class must be defined")
        
        return cls.model_class.objects.filter(**kwargs)
    
    @classmethod
    def _build_optimized_queryset(cls, select_related: List[str] = None, 
                                 prefetch_related: List[str] = None, 
                                 order_by: str = None, **filters) -> QuerySet:
        """INTERNAL USE ONLY: Build optimized queryset.
        
        This is for building complex queries within repository methods.
        The resulting queryset should be converted to list before returning.
        """
        if not cls.model_class:
            raise NotImplementedError("model_class must be defined")
        
        queryset = cls.model_class.objects.filter(**filters)
        
        if select_related:
            queryset = queryset.select_related(*select_related)
        
        if prefetch_related:
            queryset = queryset.prefetch_related(*prefetch_related)
        
        if order_by:
            queryset = queryset.order_by(order_by)
        
        return queryset