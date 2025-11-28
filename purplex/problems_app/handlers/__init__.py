"""
Activity type handler registry.

This module provides the registry for activity type handlers.
Handlers are registered using the @register_handler decorator.
"""

from typing import Dict, List, Type

from .base import ActivityHandler, ProcessingResult, ValidationResult

__all__ = [
    'ActivityHandler',
    'ValidationResult',
    'ProcessingResult',
    'register_handler',
    'get_handler',
    'get_registered_types',
    'is_registered',
]

_REGISTRY: Dict[str, Type[ActivityHandler]] = {}


def register_handler(type_name: str):
    """
    Decorator to register a handler for an activity type.

    Usage:
        @register_handler('eipl')
        class EiPLHandler(ActivityHandler):
            ...
    """
    def decorator(cls: Type[ActivityHandler]):
        if type_name in _REGISTRY:
            raise ValueError(f"Handler already registered for type: {type_name}")
        _REGISTRY[type_name] = cls
        return cls
    return decorator


def get_handler(type_name: str) -> ActivityHandler:
    """
    Get handler instance for an activity type.

    Raises ValueError if type is not registered.
    """
    if type_name not in _REGISTRY:
        raise ValueError(
            f"Unknown activity type: {type_name}. "
            f"Registered types: {list(_REGISTRY.keys())}"
        )
    return _REGISTRY[type_name]()


def get_registered_types() -> List[str]:
    """Get all registered activity type names."""
    return list(_REGISTRY.keys())


def is_registered(type_name: str) -> bool:
    """Check if a type is registered."""
    return type_name in _REGISTRY


# Import handlers to trigger registration
# This must be at the bottom to avoid circular imports
from . import eipl  # noqa: E402, F401
from . import mcq   # noqa: E402, F401
