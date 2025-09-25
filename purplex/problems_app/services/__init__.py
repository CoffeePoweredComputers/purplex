"""Services package for business logic."""

from .docker_execution_service import DockerExecutionService
from .docker_service_factory import get_shared_docker_service, cleanup_shared_service, SharedDockerServiceContext
# Alias for backwards compatibility
CodeExecutionService = DockerExecutionService
from .ai_generation_service import AITestGenerationService
from .segmentation_service import SegmentationService
from .validation_service import ProblemValidationService
from .submission_validation_service import SubmissionValidationService
from .progress_service import ProgressService
from .student_service import StudentService
from .hint_service import HintService, AdminHintService
from .hint_display_service import HintDisplayService
from .admin_service import AdminProblemService
from .course_service import CourseService

__all__ = [
    'CodeExecutionService',
    'get_shared_docker_service',
    'cleanup_shared_service',
    'AITestGenerationService',
    'SegmentationService',
    'ProblemValidationService',
    'SubmissionValidationService',
    'ProgressService',
    'StudentService',
    'HintService',
    'AdminHintService',
    'HintDisplayService',
    'AdminProblemService',
    'CourseService'
]