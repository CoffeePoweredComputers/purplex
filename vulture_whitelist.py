"""
Vulture whitelist for Django/DRF false positives.

Vulture cannot trace dynamic calls through Django's ORM, DRF's permissions,
and other framework patterns. This whitelist documents intentionally "unused"
code that is actually used by the framework.

Usage: vulture purplex/ vulture_whitelist.py --min-confidence 80

NOTE: For unused parameters like 'view', 'exc_tb', etc., the Python convention
is to prefix with underscore (_view, _exc_tb). However, DRF and Django require
these exact parameter names in their interfaces. We suppress these via
--ignore-names in the Makefile instead.
"""

# =============================================================================
# Django REST Framework Permission Classes (Mark as used)
# =============================================================================
# DRF dynamically calls these - vulture can't trace the dispatch.

from purplex.users_app.permissions import (
    CanAccessAdminPanel,
    CanManageCourse,
    CanManageProblems,
    CanSubmitCode,
    CanViewCourseAnalytics,
    CanViewResearchData,
    CanViewSubmission,
    IsAdmin,
    IsAuthenticated,
    IsCourseEnrolled,
    IsCourseInstructor,
    IsInstructor,
    IsInstructorOrAdmin,
    IsOwner,
    IsOwnerOrReadOnly,
)

# Mark the classes themselves as used (DRF dispatches to these)
IsAuthenticated
IsOwnerOrReadOnly
IsInstructorOrAdmin
IsAdmin
IsInstructor
IsCourseInstructor
IsCourseEnrolled
IsOwner
CanViewSubmission
CanSubmitCode
CanManageCourse
CanViewCourseAnalytics
CanAccessAdminPanel
CanManageProblems
CanViewResearchData


# =============================================================================
# Django Context Managers
# =============================================================================
from purplex.problems_app.services.docker_execution_service import (  # noqa: E402
    DockerExecutionService,
)
from purplex.problems_app.services.docker_service_factory import (  # noqa: E402
    DockerServiceFactory,
)

DockerExecutionService.__exit__
DockerServiceFactory.__exit__


# =============================================================================
# Mock Firebase (Development Only)
# =============================================================================
from purplex.users_app.mock_firebase import MockAuth, MockFirebaseAdmin  # noqa: E402

MockAuth.verify_id_token
MockFirebaseAdmin.list_users


# =============================================================================
# Repository Base Class Methods (Inherited by subclasses)
# =============================================================================
from purplex.problems_app.repositories.base_repository import (  # noqa: E402
    BaseRepository,
)

BaseRepository.get_by_id
BaseRepository.get_all
BaseRepository.filter_with_select_related
BaseRepository.filter_with_prefetch
BaseRepository.get_first
BaseRepository.get_last
BaseRepository.paginate
BaseRepository._get_queryset
BaseRepository._build_optimized_queryset


# =============================================================================
# Django Management Command Interface
# =============================================================================
# handle() is the entry point called by Django's command framework
# Note: Using string comments instead of _.attr syntax to avoid F821 errors
# Vulture recognizes these patterns:

# Management commands: .handle method
# Celery tasks: .delay and .apply_async methods
