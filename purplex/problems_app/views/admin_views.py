"""Admin views for managing problems, test cases, and problem sets."""

import json
import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from purplex.submissions.repositories import SubmissionRepository
from purplex.submissions.services import SubmissionService
from purplex.users_app.permissions import IsAdmin
from purplex.users_app.repositories.user_repository import UserRepository
from purplex.utils.error_codes import ErrorCode, error_response

from ..models import (
    DebugFixProblem,
    McqProblem,
    ProbeableCodeProblem,
    ProbeableSpecProblem,
    PromptProblem,
    RefuteProblem,
)
from ..serializers import (
    AdminDebugFixProblemSerializer,
    AdminMcqProblemSerializer,
    AdminProbeableCodeProblemSerializer,
    AdminProbeableSpecProblemSerializer,
    AdminProblemSerializer,
    AdminProblemSetSerializer,
    AdminPromptProblemSerializer,
    AdminRefuteProblemSerializer,
    CourseInstructorCreateSerializer,
    CourseInstructorSerializer,
    McqProblemSerializer,
    ProbeableCodeProblemSerializer,
    ProblemCategorySerializer,
    ProblemPolymorphicListSerializer,
    ProblemSetSerializer,
    RefuteProblemSerializer,
    TestCaseSerializer,
)
from ..services.admin_service import AdminProblemService
from ..services.course_service import CourseService
from ..services.docker_service_factory import SharedDockerServiceContext

logger = logging.getLogger(__name__)
SERVER_URL = getattr(settings, "SERVER_URL", "http://localhost:8000")


class AdminProblemListView(APIView):
    """Admin view for listing and creating problems."""

    permission_classes = [IsAdmin]

    def get(self, request):
        # Use service layer to get problems with optimized queries
        problems = AdminProblemService.get_all_problems_optimized()
        # Use polymorphic serializer to handle different problem types
        serializer = ProblemPolymorphicListSerializer(problems, many=True)
        return Response(serializer.data)

    def post(self, request):
        # Use service layer to prepare data
        data, problem_set_slugs = AdminProblemService.prepare_problem_data(request.data)

        # Add detailed logging to understand what data we're receiving
        logger.info(f"Creating problem with data: {data}")
        logger.info(f"Problem set slugs: {problem_set_slugs}")

        # Route to correct serializer based on problem_type
        problem_type = data.get("problem_type", "eipl")

        # Map problem types to their serializers - explicit, no silent fallback
        PROBLEM_TYPE_SERIALIZERS = {
            "eipl": AdminProblemSerializer,
            "mcq": AdminMcqProblemSerializer,
            "probeable_code": AdminProbeableCodeProblemSerializer,
            "refute": AdminRefuteProblemSerializer,
            "prompt": AdminPromptProblemSerializer,
            "debug_fix": AdminDebugFixProblemSerializer,
            "probeable_spec": AdminProbeableSpecProblemSerializer,
        }

        if problem_type not in PROBLEM_TYPE_SERIALIZERS:
            valid_types = ", ".join(sorted(PROBLEM_TYPE_SERIALIZERS.keys()))
            return Response(
                {
                    "error": f"Invalid problem_type: '{problem_type}'",
                    "code": ErrorCode.INVALID_PROBLEM_TYPE,
                    "details": f"Valid types are: {valid_types}",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PROBLEM_TYPE_SERIALIZERS[problem_type](data=data)

        if serializer.is_valid():
            try:
                with transaction.atomic():
                    problem = serializer.save(created_by=request.user)

                    # Use service layer to handle problem set assignments
                    if problem_set_slugs:
                        AdminProblemService.create_problem_with_relations(
                            problem, problem_set_slugs
                        )

                    # Return the serialized problem with correct serializer
                    # Use same mapping - already validated above
                    response_serializer = PROBLEM_TYPE_SERIALIZERS[problem_type](
                        problem
                    )
                    return Response(
                        response_serializer.data, status=status.HTTP_201_CREATED
                    )
            except Exception as e:
                logger.error(f"Failed to create problem: {str(e)}")
                return error_response(
                    "Failed to create problem. Please try again.",
                    ErrorCode.SERVER_ERROR,
                    500,
                )

        # Log the validation errors to help debug
        logger.warning(
            f"Problem creation failed with validation errors: {serializer.errors}"
        )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminProblemDetailView(APIView):
    """Admin view for getting, updating, and deleting specific problems."""

    permission_classes = [IsAdmin]

    def get(self, request, slug):
        problem = AdminProblemService.get_problem_by_slug(slug)
        if not problem:
            return error_response(
                f"Problem with slug {slug} not found",
                ErrorCode.NOT_FOUND,
                404,
            )
        # Use correct serializer based on problem type
        if isinstance(problem, McqProblem):
            serializer = McqProblemSerializer(problem)
        elif isinstance(problem, ProbeableCodeProblem):
            serializer = ProbeableCodeProblemSerializer(problem)
        elif isinstance(problem, RefuteProblem):
            serializer = RefuteProblemSerializer(problem)
        elif isinstance(problem, PromptProblem):
            serializer = AdminPromptProblemSerializer(problem)
        elif isinstance(problem, DebugFixProblem):
            serializer = AdminDebugFixProblemSerializer(problem)
        elif isinstance(problem, ProbeableSpecProblem):
            serializer = AdminProbeableSpecProblemSerializer(problem)
        else:
            serializer = AdminProblemSerializer(problem)
        return Response(serializer.data)

    def put(self, request, slug):
        problem = AdminProblemService.get_problem_by_slug(slug)
        if not problem:
            return error_response(
                f"Problem with slug {slug} not found",
                ErrorCode.NOT_FOUND,
                404,
            )

        # Use service layer to prepare data
        data, problem_sets_slugs = AdminProblemService.prepare_problem_data(
            request.data
        )

        # Use correct serializer based on problem type
        is_mcq = isinstance(problem, McqProblem)
        is_probeable_code = isinstance(problem, ProbeableCodeProblem)
        is_refute = isinstance(problem, RefuteProblem)
        is_prompt = isinstance(problem, PromptProblem)
        is_debug_fix = isinstance(problem, DebugFixProblem)
        is_probeable_spec = isinstance(problem, ProbeableSpecProblem)
        if is_mcq:
            serializer = AdminMcqProblemSerializer(problem, data=data, partial=True)
        elif is_probeable_code:
            serializer = AdminProbeableCodeProblemSerializer(
                problem, data=data, partial=True
            )
        elif is_refute:
            serializer = AdminRefuteProblemSerializer(problem, data=data, partial=True)
        elif is_prompt:
            serializer = AdminPromptProblemSerializer(problem, data=data, partial=True)
        elif is_debug_fix:
            serializer = AdminDebugFixProblemSerializer(
                problem, data=data, partial=True
            )
        elif is_probeable_spec:
            serializer = AdminProbeableSpecProblemSerializer(
                problem, data=data, partial=True
            )
        else:
            serializer = AdminProblemSerializer(problem, data=data, partial=True)

        if serializer.is_valid():
            try:
                with transaction.atomic():
                    problem = serializer.save()

                    # Use service layer to handle problem sets relationship
                    # Only update problem sets if explicitly provided in the request
                    if "problem_sets" in request.data:
                        problem_sets = AdminProblemService.get_problem_sets_by_slugs(
                            problem_sets_slugs
                        )
                        AdminProblemService.update_problem_set_relations(
                            problem, problem_sets
                        )

                    # Return fresh data with correct serializer
                    if is_mcq:
                        return Response(McqProblemSerializer(problem).data)
                    elif is_probeable_code:
                        return Response(ProbeableCodeProblemSerializer(problem).data)
                    elif is_refute:
                        return Response(RefuteProblemSerializer(problem).data)
                    elif is_prompt:
                        return Response(AdminPromptProblemSerializer(problem).data)
                    elif is_debug_fix:
                        return Response(AdminDebugFixProblemSerializer(problem).data)
                    elif is_probeable_spec:
                        return Response(
                            AdminProbeableSpecProblemSerializer(problem).data
                        )
                    return Response(AdminProblemSerializer(problem).data)
            except Exception as e:
                logger.error(f"Failed to update problem {slug}: {str(e)}")
                logger.error(f"Exception type: {type(e).__name__}")
                logger.error(f"Exception args: {e.args}")

                # Import traceback for more detailed error information
                import traceback

                logger.error(f"Full traceback: {traceback.format_exc()}")

                return error_response(
                    f"Failed to update problem: {str(e)}",
                    ErrorCode.SERVER_ERROR,
                    500,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, slug):
        problem = AdminProblemService.get_problem_by_slug(slug)
        if not problem:
            return error_response(
                f"Problem with slug {slug} not found",
                ErrorCode.NOT_FOUND,
                404,
            )

        # Use service layer to delete the problem
        result = AdminProblemService.delete_problem(problem)
        if result["success"]:
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return error_response(
                result.get("error", "Failed to delete problem"),
                ErrorCode.VALIDATION_ERROR,
                400,
            )


class AdminTestProblemView(APIView):
    """Admin view for testing problem reference solutions."""

    permission_classes = [IsAdmin]

    def post(self, request):
        """Test a problem's reference solution against its test cases"""
        problem_data = request.data

        # Basic validation
        required_fields = ["function_name", "reference_solution", "test_cases"]
        for field in required_fields:
            if not problem_data.get(field):
                return Response(
                    {
                        "success": False,
                        "error": f"{field} is required for testing",
                        "code": ErrorCode.VALIDATION_ERROR,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if not problem_data.get("test_cases") or len(problem_data["test_cases"]) == 0:
            return Response(
                {
                    "success": False,
                    "error": "At least one test case is required for testing",
                    "code": ErrorCode.VALIDATION_ERROR,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Test the reference solution using shared Docker service
        # Admin tests use inline test data, so we use shared service directly
        try:
            with SharedDockerServiceContext() as code_service:
                code_service.set_user_context(
                    str(request.user.id) if request.user.is_authenticated else None
                )
                result = code_service.test_solution(
                    problem_data["reference_solution"],
                    problem_data["function_name"],
                    problem_data.get("test_cases", []),
                )
                return Response(result)
        except Exception as e:
            logger.error(f"Reference solution testing failed: {str(e)}")
            return Response(
                {
                    "success": False,
                    "error": "Failed to test reference solution. Please check the code and try again.",
                    "code": ErrorCode.SERVER_ERROR,
                    "testsPassed": 0,
                    "totalTests": len(problem_data.get("test_cases", [])),
                    "results": [],
                }
            )


class AdminTestCaseView(APIView):
    """Admin view for managing test cases."""

    permission_classes = [IsAdmin]

    def post(self, request, problem_slug):
        """Add test case to a problem"""
        problem = AdminProblemService.get_problem_by_slug(problem_slug)
        if not problem:
            return error_response(
                f"Problem with slug {problem_slug} not found",
                ErrorCode.NOT_FOUND,
                404,
            )

        serializer = TestCaseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(problem=problem)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, problem_slug, test_case_id):
        """Update a test case"""
        test_case = AdminProblemService.get_test_case(test_case_id, problem_slug)
        if not test_case:
            return error_response(
                f"Test case {test_case_id} not found for problem {problem_slug}",
                ErrorCode.NOT_FOUND,
                404,
            )

        serializer = TestCaseSerializer(test_case, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, problem_slug, test_case_id):
        """Delete a test case"""
        test_case = AdminProblemService.get_test_case(test_case_id, problem_slug)
        if not test_case:
            return error_response(
                f"Test case {test_case_id} not found for problem {problem_slug}",
                ErrorCode.NOT_FOUND,
                404,
            )

        # Use service layer to delete the test case
        if AdminProblemService.delete_test_case(test_case_id):
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return error_response(
                "Failed to delete test case",
                ErrorCode.SERVER_ERROR,
                500,
            )


class AdminProblemSetListView(APIView):
    """Admin view for listing and creating problem sets."""

    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        problem_sets = AdminProblemService.get_all_problem_sets()
        serializer = ProblemSetSerializer(problem_sets, many=True)

        # Add full URLs for icons
        for problem_set, data in zip(problem_sets, serializer.data, strict=False):
            if problem_set.icon:
                data["icon"] = SERVER_URL + problem_set.icon.url

        return Response(serializer.data)

    def post(self, request):
        """Create a new problem set"""
        # Validate required fields
        if not request.data.get("title"):
            return Response(
                {"title": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Use service to check for duplicate title/slug
        title = request.data.get("title", "")
        error_msg = AdminProblemService.validate_problem_set_title(title)
        if error_msg:
            return Response({"title": [error_msg]}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ProblemSetSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    problem_set = serializer.save(created_by=request.user)

                    # Use service to handle problems assignment
                    problem_slugs = request.data.get("problem_slugs", [])
                    if problem_slugs:
                        result = AdminProblemService.create_problem_set_with_problems(
                            problem_set, problem_slugs
                        )
                        added_problems = result["problems_added"]
                        missing_problems = result["missing_problems"]

                    response_data = serializer.data
                    if problem_set.icon:
                        response_data["icon"] = SERVER_URL + problem_set.icon.url

                    # Add info about problems added
                    if problem_slugs:
                        response_data["problems_added"] = added_problems
                        if missing_problems:
                            response_data["warnings"] = [
                                f"Problems not found: {', '.join(missing_problems)}"
                            ]

                    return Response(response_data, status=status.HTTP_201_CREATED)

            except ValidationError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(f"Error creating problem set: {str(e)}")
                return error_response(
                    "An error occurred while creating the problem set. Please try again.",
                    ErrorCode.SERVER_ERROR,
                    500,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminProblemSetDetailView(APIView):
    """Admin view for getting, updating, and deleting specific problem sets."""

    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request, slug):
        problem_set = AdminProblemService.get_problem_set_by_slug(slug)
        if not problem_set:
            return error_response(
                f"Problem set with slug {slug} not found",
                ErrorCode.NOT_FOUND,
                404,
            )
        # Use AdminProblemSetSerializer which includes problems_detail
        serializer = AdminProblemSetSerializer(problem_set)
        data = serializer.data

        if problem_set.icon:
            data["icon"] = SERVER_URL + problem_set.icon.url

        return Response(data)

    def put(self, request, slug):
        problem_set = AdminProblemService.get_problem_set_by_slug(slug)
        if not problem_set:
            return error_response(
                f"Problem set with slug {slug} not found",
                ErrorCode.NOT_FOUND,
                404,
            )

        # Use service to check if title change would create a duplicate
        if "title" in request.data:
            error_msg = AdminProblemService.validate_problem_set_title(
                request.data["title"], current_slug=slug
            )
            if error_msg:
                return Response(
                    {"title": [error_msg]}, status=status.HTTP_400_BAD_REQUEST
                )

        serializer = ProblemSetSerializer(problem_set, data=request.data, partial=True)

        if serializer.is_valid():
            try:
                with transaction.atomic():
                    problem_set = serializer.save()

                    # Use service to handle problems update
                    problem_slugs = request.data.get("problem_slugs")
                    if problem_slugs is not None:
                        result = AdminProblemService.update_problem_set_with_problems(
                            problem_set, problem_slugs
                        )
                        added_problems = result.get("problems_updated", 0)
                        missing_problems = result.get("missing_problems", [])

                    response_data = serializer.data
                    if problem_set.icon:
                        response_data["icon"] = SERVER_URL + problem_set.icon.url

                    # Add info about problems update
                    if problem_slugs is not None:
                        response_data["problems_updated"] = added_problems
                        if missing_problems:
                            response_data["warnings"] = [
                                f"Problems not found: {', '.join(missing_problems)}"
                            ]

                    return Response(response_data)

            except ValidationError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(f"Error updating problem set: {str(e)}")
                return error_response(
                    "An error occurred while updating the problem set. Please try again.",
                    ErrorCode.SERVER_ERROR,
                    500,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, slug):
        problem_set = AdminProblemService.get_problem_set_by_slug(slug)
        if not problem_set:
            return error_response(
                f"Problem set with slug {slug} not found",
                ErrorCode.NOT_FOUND,
                404,
            )

        # Use service layer to delete the problem set
        if AdminProblemService.delete_problem_set(problem_set):
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return error_response(
                "Failed to delete problem set",
                ErrorCode.SERVER_ERROR,
                500,
            )


class AdminCategoryView(APIView):
    """Admin view for managing problem categories."""

    permission_classes = [IsAdmin]

    def get(self, request):
        categories = AdminProblemService.get_all_categories()
        serializer = ProblemCategorySerializer(categories, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ProblemCategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminSubmissionListView(APIView):
    """Admin view for listing submissions with pagination and filtering."""

    permission_classes = [IsAdmin]

    def get(self, request):
        # Get query parameters
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 25))
        search = request.query_params.get("search", "")
        submission_type = request.query_params.get("type", "")
        status_filter = request.query_params.get("status", "")
        course_filter = request.query_params.get("course", "")

        # Get paginated submissions using repository
        paginated_data = SubmissionRepository.get_paginated_submissions(
            page=page,
            page_size=page_size,
            search=search,
            submission_type=submission_type if submission_type else None,
            status_filter=status_filter if status_filter else None,
            course_filter=course_filter if course_filter else None,
        )

        paginated_submissions = paginated_data["submissions"]

        # Serialize data
        submissions_data = []
        for submission in paginated_submissions:
            submissions_data.append(
                {
                    "id": str(submission.submission_id),
                    "user": submission.user.username,
                    "problem": submission.problem.title,
                    "problem_slug": submission.problem.slug,
                    "problem_set": (
                        submission.problem_set.title if submission.problem_set else None
                    ),
                    "course": submission.course.name if submission.course else None,
                    "submission_type": submission.submission_type,
                    "score": submission.score,
                    "status": submission.completion_status,
                    "comprehension_level": submission.comprehension_level,
                    "is_correct": submission.is_correct,
                    "execution_status": submission.execution_status,
                    "submitted_at": submission.submitted_at.isoformat(),
                    "passed_all_tests": submission.passed_all_tests,
                    "execution_time_ms": submission.execution_time_ms,
                    "memory_used_mb": submission.memory_used_mb,
                }
            )

        # Get filter metadata - all available options for dropdowns
        from purplex.problems_app.repositories import (
            CourseRepository,
            ProblemSetRepository,
        )

        filter_metadata = {
            "problem_sets": ProblemSetRepository.get_all_titles(),
            "courses": CourseRepository.get_all_names(),
            "statuses": [
                "incomplete",
                "partial",
                "complete",
            ],  # Valid completion_status values
        }

        # Build response with pagination metadata and filter options
        return Response(
            {
                "results": submissions_data,
                "count": paginated_data["total_count"],
                "next": f"?page={page + 1}" if paginated_data["has_next"] else None,
                "previous": (
                    f"?page={page - 1}" if paginated_data["has_previous"] else None
                ),
                "total_pages": paginated_data["total_pages"],
                "current_page": paginated_data["current_page"],
                "filters": filter_metadata,
            }
        )

    def post(self, request):
        """Export submissions data."""
        from purplex.utils.query_monitor import query_counter

        # Get filter parameters
        filters = request.data.get("filters", {})
        format_type = request.data.get("format", "json")

        with query_counter("CSV Export", warning_threshold=10):
            # Get submissions with proper prefetching - THIS IS THE FIX!
            submissions = SubmissionRepository.export_submissions(filters)
            # Note: The repository already has prefetch_related for hint_activations__hint
            # But we need to ensure we don't trigger new queries in our loops

            # Prepare export data - now uses prefetched data
            export_data = []
            for submission in submissions:
                # Convert to list once to avoid multiple iterations triggering queries
                hint_activations = list(
                    submission.hint_activations.all()
                )  # NO EXTRA QUERIES!
                hints_count = len(hint_activations)

                if hints_count > 0:
                    hint_types = list(
                        set([ha.hint.hint_type for ha in hint_activations])
                    )
                    first_hint_time = min(
                        [ha.activated_at for ha in hint_activations]
                    ).isoformat()
                    last_hint_time = max(
                        [ha.activated_at for ha in hint_activations]
                    ).isoformat()
                else:
                    hint_types = []
                    first_hint_time = ""
                    last_hint_time = ""

                # Format hint details using already-loaded data
                hint_details = []
                for ha in hint_activations:
                    hint_details.append(
                        {
                            "type": ha.hint.hint_type,  # No extra query - hint is prefetched!
                            "trigger": ha.trigger_type,
                            "time": ha.activated_at.isoformat(),
                            "order": ha.activation_order,
                            "duration_seconds": ha.viewed_duration_seconds,
                            "helpful": ha.was_helpful,
                        }
                    )

                # Get user progress for this problem/problem_set/course context
                user_progress = None
                if hasattr(submission.user, "userprogress"):
                    # Find matching progress from prefetched data
                    for prog in submission.user.userprogress.all():
                        if (
                            prog.problem_id == submission.problem_id
                            and prog.problem_set_id == submission.problem_set_id
                            and prog.course_id == submission.course_id
                        ):
                            user_progress = prog
                            break

                # Add progress fields
                if user_progress:
                    # Calculate days since first attempt
                    days_since_first = None
                    if user_progress.first_attempt:
                        days_since_first = (
                            submission.submitted_at - user_progress.first_attempt
                        ).days

                    # Convert time spent to minutes
                    total_time_minutes = None
                    if user_progress.total_time_spent:
                        total_time_minutes = int(
                            user_progress.total_time_spent.total_seconds() / 60
                        )

                    progress_fields = {
                        "user_total_attempts": user_progress.attempts,
                        "user_best_score": user_progress.best_score,
                        "user_average_score": round(user_progress.average_score, 2),
                        "user_grade": user_progress.grade,
                        "user_completion_status": user_progress.status,
                        "user_hints_used_total": user_progress.hints_used,
                        "days_since_first_attempt": days_since_first,
                        "total_time_spent_minutes": total_time_minutes,
                        "consecutive_successes": user_progress.consecutive_successes,
                    }
                else:
                    # No progress found - fill with defaults
                    progress_fields = {
                        "user_total_attempts": 0,
                        "user_best_score": 0,
                        "user_average_score": 0.0,
                        "user_grade": "incomplete",
                        "user_completion_status": "not_started",
                        "user_hints_used_total": 0,
                        "days_since_first_attempt": None,
                        "total_time_spent_minutes": None,
                        "consecutive_successes": 0,
                    }

                # Extract segmentation data if available (for EiPL submissions)
                segmentation_fields = {}
                if hasattr(submission, "segmentation") and submission.segmentation:
                    seg = submission.segmentation
                    segmentation_fields = {
                        "segment_count": seg.segment_count,
                        "segments": json.dumps(
                            seg.segments
                        ),  # JSON array of segment descriptions
                        "segmentation_comprehension_level": seg.comprehension_level,
                        "segmentation_confidence": seg.confidence_score,
                        "segmentation_feedback": seg.feedback_message,
                        "segmentation_passed": seg.passed,
                    }
                else:
                    # Default values when no segmentation exists (direct code submissions)
                    segmentation_fields = {
                        "segment_count": None,
                        "segments": "",
                        "segmentation_comprehension_level": "",
                        "segmentation_confidence": None,
                        "segmentation_feedback": "",
                        "segmentation_passed": None,
                    }

                export_data.append(
                    {
                        "submission_id": str(submission.submission_id),
                        "user": submission.user.username,
                        "problem_id": submission.problem.id,  # ADD: Numeric problem ID
                        "problem_slug": submission.problem.slug,  # ADD: Problem slug for reference
                        "problem_title": submission.problem.title,  # Renamed from 'problem'
                        "problem_set": (
                            submission.problem_set.title
                            if submission.problem_set
                            else ""
                        ),
                        "course": submission.course.name if submission.course else "",
                        "submission_type": submission.submission_type,
                        "raw_input": submission.raw_input,  # Original user input (code or natural language)
                        "processed_code": submission.processed_code,  # Final code that was executed
                        "score": submission.score,
                        "comprehension_level": submission.comprehension_level,
                        "is_correct": submission.is_correct,
                        "status": submission.completion_status,
                        "submitted_at": submission.submitted_at.isoformat(),
                        "execution_time_ms": submission.execution_time_ms,
                        "memory_used_mb": submission.memory_used_mb,
                        "hints_activated_count": hints_count,
                        "hint_types_used": ",".join(hint_types) if hint_types else "",
                        "first_hint_time": first_hint_time,
                        "last_hint_time": last_hint_time,
                        "hint_details": (
                            json.dumps(hint_details) if hint_details else ""
                        ),
                        **segmentation_fields,  # ADD: All segmentation fields
                        **progress_fields,  # Add all progress fields
                    }
                )

        if format_type == "csv":
            # Return CSV response
            import csv

            from django.http import HttpResponse

            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="submissions.csv"'

            if export_data:
                writer = csv.DictWriter(response, fieldnames=export_data[0].keys())
                writer.writeheader()
                writer.writerows(export_data)

            return response
        else:
            return Response(export_data)


class AdminSubmissionDetailView(APIView):
    """Admin view for individual submission details."""

    permission_classes = [IsAdmin]

    def get(self, request, submission_id):
        try:
            # Get submission details using service
            submission_data = SubmissionService.get_submission_details(submission_id)
            return Response(submission_data)
        except Exception as e:
            if "DoesNotExist" in str(type(e).__name__):
                return error_response(
                    "Submission not found",
                    ErrorCode.NOT_FOUND,
                    404,
                )
            else:
                logger.error(f"Error fetching submission details: {str(e)}")
                return error_response(
                    "Failed to fetch submission details",
                    ErrorCode.SERVER_ERROR,
                    500,
                )


class AdminCourseTeamListCreateView(APIView):
    """Admin endpoint for listing and adding course team members."""

    permission_classes = [IsAdmin]

    def get(self, request, course_id):
        """List all instructors and TAs for a course."""
        course = CourseService.get_course_by_id(
            course_id, require_active=False, include_deleted=True
        )
        if not course:
            return Response(
                {"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND
            )

        instructors = CourseService.get_course_instructors(course)
        serializer = CourseInstructorSerializer(instructors, many=True)
        return Response(serializer.data)

    def post(self, request, course_id):
        """Add an instructor or TA to a course."""
        course = CourseService.get_course_by_id(
            course_id, require_active=False, include_deleted=True
        )
        if not course:
            return Response(
                {"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = CourseInstructorCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        role = serializer.validated_data["role"]
        user = UserRepository.get_by_email(serializer.validated_data["email"])

        if not user:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        try:
            ci = CourseService.add_course_instructor(
                course=course, user=user, role=role, added_by=request.user
            )
        except IntegrityError:
            return Response(
                {"error": "User is already an instructor on this course"},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            CourseInstructorSerializer(ci).data, status=status.HTTP_201_CREATED
        )


class AdminCourseTeamDetailView(APIView):
    """Admin endpoint for updating or removing course team members."""

    permission_classes = [IsAdmin]

    def patch(self, request, course_id, user_id):
        """Change an instructor's role on a course."""
        course = CourseService.get_course_by_id(
            course_id, require_active=False, include_deleted=True
        )
        if not course:
            return Response(
                {"error": "Course not found", "code": "course_not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        new_role = request.data.get("role")
        if new_role not in ("primary", "ta"):
            return Response(
                {"error": "role must be 'primary' or 'ta'", "code": "invalid_role"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = UserRepository.get_by_id(user_id)
        if not user:
            return Response(
                {"error": "User not found", "code": "user_not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        result = CourseService.update_course_instructor_role(course, user, new_role)
        if not result["success"]:
            error_msg = result["error"]
            code = "update_failed"
            if "last primary" in error_msg.lower():
                code = "last_primary"
            elif "not an instructor" in error_msg.lower():
                code = "not_instructor"
            return Response(
                {"error": error_msg, "code": code},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(CourseInstructorSerializer(result["course_instructor"]).data)

    def delete(self, request, course_id, user_id):
        """Remove an instructor or TA from a course."""
        course = CourseService.get_course_by_id(
            course_id, require_active=False, include_deleted=True
        )
        if not course:
            return Response(
                {"error": "Course not found", "code": "course_not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        user = UserRepository.get_by_id(user_id)
        if not user:
            return Response(
                {"error": "User not found", "code": "user_not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        result = CourseService.remove_course_instructor(course, user)
        if not result["success"]:
            error_msg = result["error"]
            code = "remove_failed"
            if "last primary" in error_msg.lower():
                code = "last_primary"
            elif "not an instructor" in error_msg.lower():
                code = "not_instructor"
            return Response(
                {"error": error_msg, "code": code},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)
