"""
Repository for ProblemHint model data access.
"""

from typing import Optional, List, Dict, Any
from django.db.models import Q, Count
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from purplex.problems_app.models import ProblemHint, Problem
from .base_repository import BaseRepository


class ProblemHintRepository(BaseRepository):
    """
    Repository for all ProblemHint-related database queries.
    
    This repository handles all data access for problem hints,
    including hint configuration and content management.
    """
    
    model_class = ProblemHint
    
    @classmethod
    def get_problem_hint(cls, problem: Problem, hint_type: str) -> Optional[ProblemHint]:
        """Get a specific hint for a problem by type."""
        return ProblemHint.objects.filter(
            problem=problem,
            hint_type=hint_type
        ).first()
    
    @classmethod
    def get_all_problem_hints(cls, problem: Problem) -> List:
        """Get all hints for a problem, ordered by type."""
        return list(ProblemHint.objects.filter(
            problem=problem
        ).order_by('hint_type'))
    
    @classmethod
    def get_enabled_hints(cls, problem: Problem) -> List:
        """Get all enabled hints for a problem."""
        return list(ProblemHint.objects.filter(
            problem=problem,
            is_enabled=True
        ).order_by('hint_type'))
    
    @classmethod
    def get_available_hints(cls, problem: Problem, user_attempts: int) -> List:
        """Get hints that are available based on user's attempt count."""
        return list(ProblemHint.objects.filter(
            problem=problem,
            is_enabled=True,
            min_attempts__lte=user_attempts
        ).order_by('hint_type'))
    
    @classmethod
    def create_hint(cls, problem: Problem, hint_type: str, content: Dict[str, Any],
                   is_enabled: bool = False, min_attempts: int = 3) -> ProblemHint:
        """Create a new hint for a problem."""
        hint = ProblemHint(
            problem=problem,
            hint_type=hint_type,
            content=content,
            is_enabled=is_enabled,
            min_attempts=min_attempts
        )
        
        # Validate the hint before saving
        hint.full_clean()
        hint.save()
        
        return hint
    
    @classmethod
    def update_hint_content(cls, problem: Problem, hint_type: str, 
                           content: Dict[str, Any]) -> bool:
        """Update the content of an existing hint."""
        try:
            hint = cls.get_problem_hint(problem, hint_type)
            if hint:
                hint.content = content
                hint.full_clean()  # Validate content structure
                hint.save()
                return True
        except (ValidationError, Exception):
            pass
        return False
    
    @classmethod
    def enable_hint(cls, problem: Problem, hint_type: str) -> bool:
        """Enable a specific hint for a problem."""
        updated = ProblemHint.objects.filter(
            problem=problem,
            hint_type=hint_type
        ).update(is_enabled=True)
        
        return updated > 0
    
    @classmethod
    def disable_hint(cls, problem: Problem, hint_type: str) -> bool:
        """Disable a specific hint for a problem."""
        updated = ProblemHint.objects.filter(
            problem=problem,
            hint_type=hint_type
        ).update(is_enabled=False)
        
        return updated > 0
    
    @classmethod
    def update_hint_threshold(cls, problem: Problem, hint_type: str, 
                             min_attempts: int) -> bool:
        """Update the minimum attempts threshold for a hint."""
        updated = ProblemHint.objects.filter(
            problem=problem,
            hint_type=hint_type
        ).update(min_attempts=min_attempts)
        
        return updated > 0
    
    @classmethod
    def get_hint_types_for_problem(cls, problem: Problem) -> List[str]:
        """Get all hint types configured for a problem."""
        return list(ProblemHint.objects.filter(
            problem=problem
        ).values_list('hint_type', flat=True).distinct())
    
    @classmethod
    def get_enabled_hint_types(cls, problem: Problem) -> List[str]:
        """Get enabled hint types for a problem."""
        return list(ProblemHint.objects.filter(
            problem=problem,
            is_enabled=True
        ).values_list('hint_type', flat=True).distinct())
    
    @classmethod
    def bulk_enable_hints(cls, problem: Problem, hint_types: List[str]) -> int:
        """Bulk enable multiple hint types for a problem."""
        updated = ProblemHint.objects.filter(
            problem=problem,
            hint_type__in=hint_types
        ).update(is_enabled=True)
        
        return updated
    
    @classmethod
    def bulk_disable_hints(cls, problem: Problem, hint_types: List[str]) -> int:
        """Bulk disable multiple hint types for a problem."""
        updated = ProblemHint.objects.filter(
            problem=problem,
            hint_type__in=hint_types
        ).update(is_enabled=False)
        
        return updated
    
    @classmethod
    def copy_hints_to_problem(cls, source_problem: Problem, target_problem: Problem) -> int:
        """Copy all hints from one problem to another."""
        source_hints = ProblemHint.objects.filter(problem=source_problem)
        hints_created = 0
        
        for hint in source_hints:
            # Check if hint already exists for target problem
            existing = ProblemHint.objects.filter(
                problem=target_problem,
                hint_type=hint.hint_type
            ).first()
            
            if not existing:
                ProblemHint.objects.create(
                    problem=target_problem,
                    hint_type=hint.hint_type,
                    content=hint.content.copy(),  # Deep copy the content
                    is_enabled=hint.is_enabled,
                    min_attempts=hint.min_attempts
                )
                hints_created += 1
        
        return hints_created
    
    @classmethod
    def get_problems_with_hints(cls, hint_type: Optional[str] = None,
                               enabled_only: bool = False) -> List:
        """Get all problems that have hints configured."""
        filters = {}
        
        if hint_type:
            filters['hint_type'] = hint_type
        if enabled_only:
            filters['is_enabled'] = True
        
        return list(Problem.objects.filter(
            hints__isnull=False,
            **{f'hints__{k}': v for k, v in filters.items()}
        ).distinct())
    
    @classmethod
    def get_hint_usage_statistics(cls) -> Dict[str, Any]:
        """Get statistics about hint usage across all problems."""
        total_problems_with_hints = Problem.objects.filter(
            hints__isnull=False
        ).distinct().count()
        
        hint_type_stats = ProblemHint.objects.values('hint_type').annotate(
            total_count=Count('id'),
            enabled_count=Count('id', filter=Q(is_enabled=True))
        )
        
        stats = {
            'total_problems_with_hints': total_problems_with_hints,
            'hint_type_breakdown': {}
        }
        
        for stat in hint_type_stats:
            hint_type = stat['hint_type']
            stats['hint_type_breakdown'][hint_type] = {
                'total': stat['total_count'],
                'enabled': stat['enabled_count'],
                'disabled': stat['total_count'] - stat['enabled_count']
            }
        
        return stats
    
    @classmethod
    def get_problems_by_hint_configuration(cls, hint_type: str, 
                                          has_hint: bool = True,
                                          is_enabled: Optional[bool] = None) -> List:
        """Get problems filtered by hint configuration."""
        if has_hint:
            filters = {'hints__hint_type': hint_type}
            if is_enabled is not None:
                filters['hints__is_enabled'] = is_enabled
            
            return list(Problem.objects.filter(**filters).distinct())
        else:
            # Problems that don't have this hint type
            return list(Problem.objects.exclude(
                hints__hint_type=hint_type
            ).distinct())
    
    @classmethod
    def validate_hint_content(cls, hint_type: str, content: Dict[str, Any]) -> tuple:
        """
        Validate hint content structure based on hint type.
        
        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        try:
            # Create a temporary hint instance for validation
            temp_hint = ProblemHint(
                hint_type=hint_type,
                content=content
            )
            temp_hint.clean()
            return True, None
        except ValidationError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    @classmethod
    def get_hint_templates(cls) -> Dict[str, Dict[str, Any]]:
        """Get default templates for each hint type."""
        return {
            'variable_fade': {
                'mappings': [
                    {'from': 'variable_name', 'to': 'descriptive_name'}
                ]
            },
            'subgoal_highlight': {
                'subgoals': [
                    {
                        'text': 'Step 1: Description',
                        'line_ranges': [[1, 3]]
                    }
                ]
            },
            'suggested_trace': {
                'trace_steps': [
                    {
                        'line': 1,
                        'description': 'Initialize variables',
                        'variables': {'var1': 'value1'}
                    }
                ]
            }
        }
    
    @classmethod
    def create_default_hints(cls, problem: Problem, hint_types: List[str] = None) -> int:
        """Create default hint configurations for a problem."""
        if hint_types is None:
            hint_types = ['variable_fade', 'subgoal_highlight', 'suggested_trace']
        
        templates = cls.get_hint_templates()
        hints_created = 0
        
        for hint_type in hint_types:
            if hint_type in templates:
                existing = cls.get_problem_hint(problem, hint_type)
                if not existing:
                    cls.create_hint(
                        problem=problem,
                        hint_type=hint_type,
                        content=templates[hint_type],
                        is_enabled=False,  # Start disabled by default
                        min_attempts=3
                    )
                    hints_created += 1
        
        return hints_created
    
    @classmethod
    def delete_problem_hints(cls, problem: Problem, hint_types: List[str] = None) -> int:
        """Delete hints for a problem. If hint_types not provided, deletes all hints."""
        filters = {'problem': problem}
        
        if hint_types:
            filters['hint_type__in'] = hint_types
        
        deleted, _ = ProblemHint.objects.filter(**filters).delete()
        return deleted
    
    @classmethod
    def search_hints_by_content(cls, search_term: str) -> List:
        """Search for hints by content (useful for finding examples)."""
        return list(ProblemHint.objects.filter(
            Q(content__icontains=search_term)
        ).select_related('problem').order_by('problem__title', 'hint_type'))