"""
Instructor content management views.
Ownership-scoped CRUD operations for problems, problem sets, and courses.
"""

import logging
from datetime import datetime

from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from purplex.users_app.permissions import (
    IsCourseInstructor,
    IsInstructor,
    IsInstructorAndOwner,
)

from ..models import (
    CourseProblemSet,
    McqProblem,
    ProbeableCodeProblem,
    ProblemSet,
    RefuteProblem,
)
from ..repositories import CourseRepository
from ..serializers import (
    AdminMcqProblemSerializer,
    AdminProbeableCodeProblemSerializer,
    AdminProblemSerializer,
    AdminProblemSetSerializer,
    AdminRefuteProblemSerializer,
    CourseCreateUpdateSerializer,
    CourseDetailSerializer,
    McqProblemSerializer,
    ProbeableCodeProblemSerializer,
    ProblemPolymorphicListSerializer,
    ProblemSetSerializer,
    RefuteProblemSerializer,
)
from ..services.admin_service import AdminProblemService
from ..services.instructor_content_service import InstructorContentService

logger = logging.getLogger(__name__)


def get_serializer_for_problem(problem, for_write=False):
    """Get the appropriate serializer class for a problem type."""
    if isinstance(problem, McqProblem):
        return AdminMcqProblemSerializer if for_write else McqProblemSerializer
    elif isinstance(problem, ProbeableCodeProblem):
        return (
            AdminProbeableCodeProblemSerializer
            if for_write
            else ProbeableCodeProblemSerializer
        )
    elif isinstance(problem, RefuteProblem):
        return AdminRefuteProblemSerializer if for_write else RefuteProblemSerializer
    else:
        return AdminProblemSerializer


def get_serializer_for_problem_type(problem_type, for_write=False):
    """Get the appropriate serializer class for a problem type string."""
    if problem_type == "mcq":
        return AdminMcqProblemSerializer if for_write else McqProblemSerializer
    elif problem_type == "probeable_code":
        return (
            AdminProbeableCodeProblemSerializer
            if for_write
            else ProbeableCodeProblemSerializer
        )
    elif problem_type == "refute":
        return AdminRefuteProblemSerializer if for_write else RefuteProblemSerializer
    else:
        return AdminProblemSerializer


class InstructorCourseCreateView(APIView):
    """POST: Create a new course (instructor becomes owner)."""

    permission_classes = [IsInstructor]

    def post(self, request):
        # Security: Strip instructor_id - instructors can only create courses they own
        data = {k: v for k, v in request.data.items() if k != "instructor_id"}
        serializer = CourseCreateUpdateSerializer(data=data)
        if serializer.is_valid():
            # Follow DRF pattern: pass instructor via save() like problem creation does
            course = serializer.save(instructor=request.user)
            return Response(
                CourseDetailSerializer(course).data, status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InstructorProblemListView(APIView):
    """GET: List instructor's problems. POST: Create new problem."""

    permission_classes = [IsInstructor]

    def get(self, request):
        problems = InstructorContentService.get_instructor_problems(request.user)
        serializer = ProblemPolymorphicListSerializer(problems, many=True)
        return Response(serializer.data)

    def post(self, request):
        data, problem_set_slugs = AdminProblemService.prepare_problem_data(request.data)
        problem_type = data.get("problem_type", "eipl")

        SerializerClass = get_serializer_for_problem_type(problem_type, for_write=True)
        serializer = SerializerClass(data=data)

        if serializer.is_valid():
            try:
                with transaction.atomic():
                    problem = serializer.save(created_by=request.user)
                    if problem_set_slugs:
                        AdminProblemService.create_problem_with_relations(
                            problem, problem_set_slugs
                        )

                    ResponseSerializerClass = get_serializer_for_problem_type(
                        problem_type, for_write=False
                    )
                    return Response(
                        ResponseSerializerClass(problem).data,
                        status=status.HTTP_201_CREATED,
                    )
            except Exception as e:
                logger.error(f"Failed to create problem: {str(e)}")
                return Response(
                    {"error": "Failed to create problem. Please try again."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InstructorProblemDetailView(APIView):
    """GET/PUT/DELETE: Manage own problems."""

    permission_classes = [IsInstructorAndOwner]

    def get_object(self, request, slug):
        problem = InstructorContentService.get_instructor_problem(request.user, slug)
        if problem:
            self.check_object_permissions(request, problem)
        return problem

    def get(self, request, slug):
        problem = self.get_object(request, slug)
        if not problem:
            return Response(
                {"error": "Problem not found or not owned by you"},
                status=status.HTTP_404_NOT_FOUND,
            )
        SerializerClass = get_serializer_for_problem(problem, for_write=False)
        return Response(SerializerClass(problem).data)

    def put(self, request, slug):
        problem = self.get_object(request, slug)
        if not problem:
            return Response(
                {"error": "Problem not found or not owned by you"},
                status=status.HTTP_404_NOT_FOUND,
            )

        data, problem_set_slugs = AdminProblemService.prepare_problem_data(request.data)
        SerializerClass = get_serializer_for_problem(problem, for_write=True)
        serializer = SerializerClass(problem, data=data, partial=True)

        if serializer.is_valid():
            try:
                with transaction.atomic():
                    updated = serializer.save()
                    if "problem_sets" in request.data:
                        problem_sets = AdminProblemService.get_problem_sets_by_slugs(
                            problem_set_slugs
                        )
                        AdminProblemService.update_problem_set_relations(
                            updated, problem_sets
                        )
                    ResponseSerializerClass = get_serializer_for_problem(
                        updated, for_write=False
                    )
                    return Response(ResponseSerializerClass(updated).data)
            except Exception as e:
                logger.error(f"Failed to update problem {slug}: {str(e)}")
                return Response(
                    {"error": f"Failed to update problem: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, slug):
        problem = self.get_object(request, slug)
        if not problem:
            return Response(
                {"error": "Problem not found or not owned by you"},
                status=status.HTTP_404_NOT_FOUND,
            )
        result = AdminProblemService.delete_problem(problem)
        if result["success"]:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({"error": result["error"]}, status=status.HTTP_400_BAD_REQUEST)


class InstructorTestProblemView(APIView):
    """POST: Test a problem's reference solution."""

    permission_classes = [IsInstructor]

    def post(self, request):
        # Reuse admin test logic
        from .admin_views import AdminTestProblemView

        return AdminTestProblemView().post(request)


class InstructorProblemSetListView(APIView):
    """GET: List instructor's problem sets. POST: Create new."""

    permission_classes = [IsInstructor]

    def get(self, request):
        problem_sets = InstructorContentService.get_instructor_problem_sets(
            request.user
        )
        serializer = ProblemSetSerializer(problem_sets, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ProblemSetSerializer(data=request.data)
        if serializer.is_valid():
            problem_set = serializer.save(created_by=request.user)
            return Response(
                ProblemSetSerializer(problem_set).data, status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InstructorProblemSetDetailView(APIView):
    """GET/PUT/DELETE: Manage own problem sets."""

    permission_classes = [IsInstructorAndOwner]

    def get_object(self, request, slug):
        ps = InstructorContentService.get_instructor_problem_set(request.user, slug)
        if ps:
            self.check_object_permissions(request, ps)
        return ps

    def get(self, request, slug):
        ps = self.get_object(request, slug)
        if not ps:
            return Response(
                {"error": "Problem set not found or not owned by you"},
                status=status.HTTP_404_NOT_FOUND,
            )
        # Use AdminProblemSetSerializer to include problems_detail
        return Response(AdminProblemSetSerializer(ps).data)

    def put(self, request, slug):
        ps = self.get_object(request, slug)
        if not ps:
            return Response(
                {"error": "Problem set not found or not owned by you"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ProblemSetSerializer(ps, data=request.data, partial=True)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    ps = serializer.save()

                    # Handle problem_slugs if provided
                    problem_slugs = request.data.get("problem_slugs")
                    if problem_slugs is not None:
                        result = AdminProblemService.update_problem_set_with_problems(
                            ps, problem_slugs
                        )
                        response_data = serializer.data
                        response_data["problems_updated"] = result.get(
                            "problems_updated", 0
                        )
                        missing = result.get("missing_problems", [])
                        if missing:
                            response_data["warnings"] = [
                                f"Problems not found: {', '.join(missing)}"
                            ]
                        return Response(response_data)

                    return Response(serializer.data)
            except Exception as e:
                logger.error(f"Failed to update problem set {slug}: {str(e)}")  # nosec B608
                return Response(
                    {"error": f"Failed to update problem set: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, slug):
        ps = self.get_object(request, slug)
        if not ps:
            return Response(
                {"error": "Problem set not found or not owned by you"},
                status=status.HTTP_404_NOT_FOUND,
            )
        ps.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class InstructorCourseProblemSetManageView(APIView):
    """POST: Add problem set to course. DELETE: Remove from course."""

    permission_classes = [IsCourseInstructor]

    def post(self, request, course_id):
        course = CourseRepository.get_course_by_id(course_id)
        if not course:
            return Response(
                {"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND
            )

        self.check_object_permissions(request, course)

        problem_set_slug = request.data.get("problem_set_slug")
        order = request.data.get("order", 0)
        is_required = request.data.get("is_required", True)

        try:
            ps = ProblemSet.objects.get(slug=problem_set_slug)
        except ProblemSet.DoesNotExist:
            return Response(
                {"error": "Problem set not found"}, status=status.HTTP_404_NOT_FOUND
            )

        cps, created = CourseProblemSet.objects.get_or_create(
            course=course,
            problem_set=ps,
            defaults={"order": order, "is_required": is_required},
        )

        return Response(
            {
                "message": "Problem set added"
                if created
                else "Problem set already in course"
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request, course_id, problem_set_slug=None, membership_id=None):
        try:
            course = CourseRepository.get_course_by_id(course_id)
            if not course:
                return Response(
                    {"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND
                )

            self.check_object_permissions(request, course)

            # Support deletion by membership_id (from URL) or problem_set_slug
            if membership_id:
                deleted, _ = CourseProblemSet.objects.filter(
                    id=membership_id, course=course
                ).delete()
            else:
                slug = problem_set_slug or request.data.get("problem_set_slug")
                deleted, _ = CourseProblemSet.objects.filter(
                    course=course, problem_set__slug=slug
                ).delete()

            if deleted:
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(
                {"error": "Problem set not in course"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Delete failed: {type(e).__name__}: {str(e)}")
            return Response(
                {"error": f"Delete failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def patch(self, request, course_id, problem_set_slug=None, membership_id=None):
        """Update a CourseProblemSet (order, is_required, due_date)."""
        try:
            course = CourseRepository.get_course_by_id(course_id)
            if not course:
                return Response(
                    {"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND
                )

            self.check_object_permissions(request, course)

            # Get the CourseProblemSet by membership_id (URL param or body) or problem_set_slug
            membership_id = membership_id or request.data.get("membership_id")
            if membership_id:
                try:
                    cps = CourseProblemSet.objects.get(id=membership_id, course=course)
                except CourseProblemSet.DoesNotExist:
                    return Response(
                        {"error": "Problem set membership not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            elif problem_set_slug:
                try:
                    cps = CourseProblemSet.objects.get(
                        course=course, problem_set__slug=problem_set_slug
                    )
                except CourseProblemSet.DoesNotExist:
                    return Response(
                        {"error": "Problem set not in course"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            else:
                return Response(
                    {"error": "membership_id or problem_set_slug required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Update fields if provided
            if "order" in request.data:
                cps.order = request.data["order"]
            if "is_required" in request.data:
                cps.is_required = request.data["is_required"]
            if "due_date" in request.data:
                # Handle null/empty to clear due date
                due_date_str = request.data["due_date"]
                if due_date_str:
                    # Parse ISO 8601 format (e.g., "2050-04-02T15:00:00.000Z")
                    if due_date_str.endswith("Z"):
                        due_date_str = due_date_str[:-1] + "+00:00"
                    cps.due_date = datetime.fromisoformat(due_date_str)
                else:
                    cps.due_date = None
            if "deadline_type" in request.data:
                deadline_type = request.data["deadline_type"]
                valid_types = ["none", "soft", "hard"]
                if deadline_type not in valid_types:
                    return Response(
                        {
                            "error": f"Invalid deadline_type. Must be one of: {valid_types}"
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                cps.deadline_type = deadline_type

            cps.save()

            return Response(
                {
                    "id": cps.id,
                    "problem_set_slug": cps.problem_set.slug,
                    "problem_set_title": cps.problem_set.title,
                    "order": cps.order,
                    "is_required": cps.is_required,
                    "due_date": cps.due_date.isoformat() if cps.due_date else None,
                    "deadline_type": cps.deadline_type,
                }
            )
        except ValueError as e:
            logger.error(f"Patch failed - ValueError: {str(e)}")
            return Response(
                {"error": f"Invalid data: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Patch failed: {type(e).__name__}: {str(e)}")
            return Response(
                {"error": f"Update failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
