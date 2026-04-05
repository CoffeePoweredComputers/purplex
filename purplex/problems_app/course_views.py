"""
Course management views for the Purplex platform
"""

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from purplex.problems_app.repositories import CourseInstructorRepository
from purplex.users_app.permissions import IsAdmin, IsCourseInstructor, IsInstructor
from purplex.users_app.repositories.user_repository import UserRepository
from purplex.utils.error_codes import ErrorCode, error_response

from .serializers import (
    CourseCreateUpdateSerializer,
    CourseDetailSerializer,
    CourseEnrollSerializer,
    CourseListSerializer,
    CourseLookupSerializer,
    InstructorCourseListSerializer,
)
from .services.course_service import CourseService

logger = logging.getLogger(__name__)


# Admin-Only Course Management
class AdminInstructorsListView(APIView):
    """Admin endpoint for listing users who can be instructors"""

    permission_classes = [IsAdmin]

    def get(self, request):
        """List all users who can be assigned as instructors"""
        # Get all active users (admins and instructors) using repository
        users = UserRepository.get_active_users()

        user_list = [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.get_full_name() or user.username,
                "is_staff": user.is_staff,
            }
            for user in users
        ]

        return Response(user_list)


class AdminCourseListCreateView(APIView):
    """Admin endpoint for listing and creating courses"""

    permission_classes = [IsAdmin]

    def get(self, request):
        """List all courses (including deleted for admins)"""
        active_only = request.query_params.get("active_only") == "true"

        if active_only:
            courses = CourseService.get_active_courses_with_stats()
        else:
            courses = CourseService.get_all_courses_with_stats()

        serializer = CourseListSerializer(courses, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Create a new course"""
        serializer = CourseCreateUpdateSerializer(data=request.data)
        if serializer.is_valid():
            # Get instructor from instructor_id or default to current user
            instructor_id = serializer.validated_data.pop("instructor_id", None)
            if instructor_id:
                instructor = UserRepository.get_by_id(instructor_id)
                if not instructor:
                    return error_response(
                        "Instructor not found", ErrorCode.NOT_FOUND, 400
                    )
            else:
                instructor = request.user

            course = CourseService.create_course(
                instructor=instructor, **serializer.validated_data
            )
            return Response(
                CourseDetailSerializer(course).data, status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminCourseDetailView(APIView):
    """Admin endpoint for course details, updates, and deletion"""

    permission_classes = [IsAdmin]

    def get(self, request, course_id):
        """Get course details"""
        course = CourseService.get_course_by_id(
            course_id, require_active=False, include_deleted=True
        )
        if not course:
            return error_response("Course not found", ErrorCode.NOT_FOUND, 404)

        serializer = CourseDetailSerializer(course)
        return Response(serializer.data)

    def put(self, request, course_id):
        """Update course details"""
        course = CourseService.get_course_by_id(
            course_id, require_active=False, include_deleted=True
        )
        if not course:
            return error_response("Course not found", ErrorCode.NOT_FOUND, 404)

        serializer = CourseCreateUpdateSerializer(
            course, data=request.data, partial=True
        )
        if serializer.is_valid():
            instructor_id = serializer.validated_data.pop("instructor_id", None)

            updated_course = CourseService.update_course(
                course, **serializer.validated_data
            )

            # Update primary instructor if admin changed it
            if instructor_id is not None:
                new_instructor = UserRepository.get_by_id(instructor_id)
                if not new_instructor:
                    return error_response(
                        "Instructor not found", ErrorCode.NOT_FOUND, 400
                    )
                current_role = CourseInstructorRepository.get_role(
                    new_instructor, course
                )
                if current_role is None:
                    CourseService.add_course_instructor(
                        course, new_instructor, role="primary", added_by=request.user
                    )
                elif current_role != "primary":
                    CourseService.update_course_instructor_role(
                        course, new_instructor, "primary"
                    )

            return Response(CourseDetailSerializer(updated_course).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, course_id):
        """Partial update course details (same as PUT, already partial)."""
        return self.put(request, course_id)

    def delete(self, request, course_id):
        """Soft delete a course"""
        course = CourseService.get_course_by_id(
            course_id, require_active=False, include_deleted=True
        )
        if not course:
            return error_response("Course not found", ErrorCode.NOT_FOUND, 404)

        CourseService.soft_delete_course(course)
        return Response(
            {"message": "Course deleted successfully"},
            status=status.HTTP_204_NO_CONTENT,
        )


# Instructor Views
class InstructorCourseListView(APIView):
    """List courses for an instructor"""

    permission_classes = [IsInstructor]

    def get(self, request):
        """List instructor's courses"""
        courses = CourseService.get_instructor_courses(request.user)
        serializer = InstructorCourseListSerializer(courses, many=True)
        return Response(serializer.data)


class InstructorCourseDetailView(APIView):
    """Get and update course details for instructor."""

    permission_classes = [IsCourseInstructor]

    def get(self, request, course_id):
        """Get course details"""
        course = CourseService.get_course_by_id(course_id, require_active=True)
        if not course:
            return error_response("Course not found", ErrorCode.NOT_FOUND, 404)

        # Check object-level permission
        self.check_object_permissions(request, course)

        serializer = CourseDetailSerializer(course)
        return Response(serializer.data)

    def patch(self, request, course_id):
        """Update course details (primary instructor only)."""
        course = CourseService.get_course_by_id(course_id, require_active=True)
        if not course:
            return error_response("Course not found", ErrorCode.NOT_FOUND, 404)

        self.check_object_permissions(request, course)

        # Only primary instructors can edit course details
        if not course.is_primary_instructor(request.user):
            return error_response(
                "Only the primary instructor can edit course details",
                ErrorCode.FORBIDDEN,
                403,
            )

        serializer = CourseCreateUpdateSerializer(
            course, data=request.data, partial=True
        )
        if serializer.is_valid():
            # instructor_id is handled via the team management API
            serializer.validated_data.pop("instructor_id", None)

            updated_course = CourseService.update_course(
                course, **serializer.validated_data
            )
            return Response(CourseDetailSerializer(updated_course).data)
        # Format validation errors consistently with the rest of the API
        first_error = next(iter(serializer.errors.values()), ["Validation failed"])[0]
        return error_response(str(first_error), ErrorCode.VALIDATION_ERROR, 400)

    def delete(self, request, course_id):
        """Soft delete a course (primary instructor only)."""
        course = CourseService.get_course_by_id(course_id, require_active=True)
        if not course:
            return error_response("Course not found", ErrorCode.NOT_FOUND, 404)

        self.check_object_permissions(request, course)

        if not course.is_primary_instructor(request.user):
            return error_response(
                "Only the primary instructor can delete a course",
                ErrorCode.FORBIDDEN,
                403,
            )

        CourseService.soft_delete_course(course)
        return Response(status=status.HTTP_204_NO_CONTENT)


class InstructorCourseStudentsView(APIView):
    """View enrolled students for a course with per-problem-set progress"""

    permission_classes = [IsCourseInstructor]

    def get(self, request, course_id):
        """List enrolled students with problem set progress"""
        course = CourseService.get_course_by_id(course_id, require_active=True)
        if not course:
            return error_response("Course not found", ErrorCode.NOT_FOUND, 404)

        self.check_object_permissions(request, course)

        # Returns dict with 'problem_sets' and 'students' keys
        data = CourseService.get_instructor_course_students(course)
        return Response(data)


class InstructorCourseProgressView(APIView):
    """View student progress in a course"""

    permission_classes = [IsCourseInstructor]

    def get(self, request, course_id):
        """Get all student progress for the course"""
        course = CourseService.get_course_by_id(course_id, require_active=True)
        if not course:
            return error_response("Course not found", ErrorCode.NOT_FOUND, 404)

        self.check_object_permissions(request, course)

        progress_data = CourseService.get_instructor_course_progress(course)
        return Response(progress_data)


class InstructorCourseProblemSetOrderView(APIView):
    """Reorder problem sets in a course"""

    permission_classes = [IsCourseInstructor]

    def put(self, request, course_id):
        """Update problem set ordering"""
        course = CourseService.get_course_by_id(course_id, require_active=True)
        if not course:
            return error_response("Course not found", ErrorCode.NOT_FOUND, 404)

        self.check_object_permissions(request, course)

        # Expect data like: [{"problem_set_id": 1, "order": 0}, ...]
        ordering_data = request.data.get("ordering", [])

        success = CourseService.reorder_course_problem_sets(course, ordering_data)

        if success:
            return Response({"message": "Problem sets reordered successfully"})
        else:
            return error_response(
                "Failed to reorder problem sets", ErrorCode.SERVER_ERROR, 500
            )


# Student Course Views
class StudentEnrolledCoursesView(APIView):
    """List courses a student is enrolled in with full progress data"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get enrolled courses with embedded problem set progress"""
        courses_data = CourseService.get_student_enrolled_courses_with_progress(
            request.user
        )
        return Response(courses_data)


class CourseLookupView(APIView):
    """Lookup a course by ID for enrollment"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Lookup course details"""
        serializer = CourseLookupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        course_id = serializer.validated_data["course_id"]

        result = CourseService.lookup_course_for_enrollment(course_id, request.user)

        if not result["success"]:
            return error_response(result["error"], ErrorCode.NOT_FOUND, 404)

        course = result["course"]
        already_enrolled = result["already_enrolled"]

        instructor_name = (
            CourseInstructorRepository.get_primary_instructor_names(course)
            or "Unknown Instructor"
        )

        return Response(
            {
                "course": {
                    "course_id": course.course_id,
                    "name": course.name,
                    "description": course.description,
                    "instructor": instructor_name,
                    "problem_sets_count": course.problem_sets.count(),
                    "enrollment_open": course.enrollment_open,
                },
                "already_enrolled": already_enrolled,
            }
        )


class CourseEnrollView(APIView):
    """Enroll in a course"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Enroll user in course"""
        serializer = CourseEnrollSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        course_id = serializer.validated_data["course_id"]

        result = CourseService.enroll_user_in_course(request.user, course_id)

        if not result["success"]:
            return error_response(result["error"], ErrorCode.VALIDATION_ERROR, 400)

        course = result["course"]
        enrollment = result["enrollment"]
        created = result["created"]

        return Response(
            {
                "success": True,
                "course": CourseDetailSerializer(course).data,
                "enrolled_at": enrollment.enrolled_at,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class StudentCourseDetailView(APIView):
    """Get course details for enrolled students"""

    permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
        """Get course with problem sets"""
        course = CourseService.get_course_by_id(course_id, require_active=True)
        if not course:
            return error_response("Course not found", ErrorCode.NOT_FOUND, 404)

        # Check enrollment using service
        if not CourseService.is_user_enrolled(request.user, course_id):
            return error_response(
                "You are not enrolled in this course",
                ErrorCode.NOT_ENROLLED,
                403,
            )

        serializer = CourseDetailSerializer(course)
        return Response(serializer.data)


class StudentCourseProgressView(APIView):
    """Get student's own progress in a course"""

    permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
        """Get progress for the requesting user"""
        result = CourseService.get_student_course_progress(request.user, course_id)

        if not result["success"]:
            if "not found" in result["error"].lower():
                return error_response(result["error"], ErrorCode.NOT_FOUND, 404)
            return error_response(result["error"], ErrorCode.NOT_ENROLLED, 403)

        return Response(result["progress"])


# New Admin Views for Course Action Buttons


class AdminCourseProblemSetsView(APIView):
    """Admin endpoint for managing problem sets in a course"""

    permission_classes = [IsAdmin]

    def get(self, request, course_id):
        """Get all problem sets assigned to a course"""
        course = CourseService.get_course_by_id(
            course_id, require_active=False, include_deleted=True
        )
        if not course:
            return error_response("Course not found", ErrorCode.NOT_FOUND, 404)

        # Get problem sets with their order and required status
        course_problem_sets = CourseService.get_course_problem_sets(course)

        response_data = []
        for cps in course_problem_sets:
            response_data.append(
                {
                    "id": cps["course_problem_set_id"],
                    "problem_set": {
                        "slug": cps["problem_set"]["slug"],
                        "title": cps["problem_set"]["title"],
                        "problems_count": cps["problem_set"]["problems_count"],
                    },
                    "order": cps["order"],
                    "is_required": cps["is_required"],
                    "due_date": cps["due_date"],
                    "deadline_type": cps["deadline_type"],
                    "added_at": cps.get("added_at"),  # This might not be in the dict
                }
            )

        return Response(response_data)

    def post(self, request, course_id):
        """Add a problem set to a course"""
        course = CourseService.get_course_by_id(
            course_id, require_active=False, include_deleted=True
        )
        if not course:
            return error_response("Course not found", ErrorCode.NOT_FOUND, 404)

        problem_set_slug = request.data.get("problem_set_slug")
        is_required = request.data.get("is_required", False)
        order = request.data.get("order")

        if not problem_set_slug:
            return error_response(
                "problem_set_slug is required", ErrorCode.VALIDATION_ERROR, 400
            )

        result = CourseService.add_problem_set_to_course(
            course, problem_set_slug, order, is_required
        )

        if not result["success"]:
            error_code = (
                ErrorCode.NOT_FOUND
                if "not found" in result["error"].lower()
                else ErrorCode.VALIDATION_ERROR
            )
            error_status = 404 if "not found" in result["error"].lower() else 400
            return error_response(result["error"], error_code, error_status)

        course_ps = result["course_problem_set"]
        problem_set = result["problem_set"]

        return Response(
            {
                "id": course_ps.id,
                "problem_set": {
                    "slug": problem_set.slug,
                    "title": problem_set.title,
                    "problems_count": problem_set.problems.count(),
                },
                "order": course_ps.order,
                "is_required": course_ps.is_required,
                "added_at": course_ps.added_at,
            },
            status=status.HTTP_201_CREATED,
        )

    def put(self, request, course_id, problem_set_slug):
        """Update problem set order or required status in course"""
        course = CourseService.get_course_by_id(
            course_id, require_active=False, include_deleted=True
        )
        if not course:
            return error_response("Course not found", ErrorCode.NOT_FOUND, 404)

        # Extract update data
        update_data = {}
        if "order" in request.data:
            update_data["order"] = request.data["order"]
        if "is_required" in request.data:
            update_data["is_required"] = request.data["is_required"]

        result = CourseService.update_course_problem_set(
            course, problem_set_slug, **update_data
        )

        if not result["success"]:
            return error_response(result["error"], ErrorCode.NOT_FOUND, 404)

        course_ps = result["course_problem_set"]

        return Response(
            {
                "id": course_ps.id,
                "problem_set": {
                    "slug": course_ps.problem_set.slug,
                    "title": course_ps.problem_set.title,
                    "problems_count": course_ps.problem_set.problems.count(),
                },
                "order": course_ps.order,
                "is_required": course_ps.is_required,
                "due_date": course_ps.due_date.isoformat()
                if course_ps.due_date
                else None,
                "deadline_type": course_ps.deadline_type,
            }
        )

    def delete(self, request, course_id, problem_set_slug):
        """Remove a problem set from a course"""
        course = CourseService.get_course_by_id(
            course_id, require_active=False, include_deleted=True
        )
        if not course:
            return error_response("Course not found", ErrorCode.NOT_FOUND, 404)

        result = CourseService.remove_problem_set_from_course(course, problem_set_slug)

        if not result["success"]:
            return error_response(result["error"], ErrorCode.NOT_FOUND, 404)

        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminAvailableProblemSetsView(APIView):
    """Get problem sets not assigned to a specific course"""

    permission_classes = [IsAdmin]

    def get(self, request):
        """List problem sets available to add to a course"""
        exclude_course_id = request.query_params.get("exclude_course")

        available_problem_sets = CourseService.get_available_problem_sets(
            exclude_course_id
        )

        response_data = []
        for ps in available_problem_sets:
            response_data.append(
                {
                    "slug": ps["slug"],
                    "title": ps["title"],
                    "problems_count": ps["problems_count"],
                    "description": ps["description"],
                }
            )

        return Response(response_data)


class AdminCourseAvailableProblemSetsView(APIView):
    """Get problem sets not yet assigned to a specific course (path param version)."""

    permission_classes = [IsAdmin]

    def get(self, request, course_id):
        """List problem sets available to add to this course."""
        available_problem_sets = CourseService.get_available_problem_sets(
            exclude_course_id=course_id
        )

        response_data = [
            {
                "slug": ps["slug"],
                "title": ps["title"],
                "problems_count": ps["problems_count"],
                "description": ps["description"],
            }
            for ps in available_problem_sets
        ]

        return Response(response_data)


class InstructorCourseAvailableProblemSetsView(APIView):
    """Get problem sets not yet assigned to an instructor's course."""

    permission_classes = [IsCourseInstructor]

    def get(self, request, course_id):
        """List problem sets available to add to this course."""
        # Verify instructor owns this course
        course = CourseService.get_course_by_id(course_id)
        if not course:
            return error_response("Course not found", ErrorCode.NOT_FOUND, 404)

        self.check_object_permissions(request, course)

        available_problem_sets = CourseService.get_available_problem_sets(
            exclude_course_id=course_id
        )

        response_data = [
            {
                "slug": ps["slug"],
                "title": ps["title"],
                "problems_count": ps["problems_count"],
                "description": ps["description"],
            }
            for ps in available_problem_sets
        ]

        return Response(response_data)


class AdminCourseStudentsView(APIView):
    """Admin endpoint for managing students in a course"""

    permission_classes = [IsAdmin]

    def get(self, request, course_id):
        """Get all students enrolled in a course with progress info"""
        course = CourseService.get_course_by_id(
            course_id, require_active=False, include_deleted=True
        )
        if not course:
            return error_response("Course not found", ErrorCode.NOT_FOUND, 404)

        students_data = CourseService.get_course_students_with_progress(course)
        return Response(students_data)

    def delete(self, request, course_id, user_id):
        """Remove a student from a course"""
        course = CourseService.get_course_by_id(
            course_id, require_active=False, include_deleted=True
        )
        if not course:
            return error_response("Course not found", ErrorCode.NOT_FOUND, 404)

        result = CourseService.remove_student_from_course(course, user_id)

        if not result["success"]:
            error_code = (
                ErrorCode.NOT_FOUND
                if "not found" in result["error"].lower()
                else ErrorCode.VALIDATION_ERROR
            )
            error_status = 404 if "not found" in result["error"].lower() else 400
            return error_response(result["error"], error_code, error_status)

        return Response(
            {"message": result["message"]}, status=status.HTTP_204_NO_CONTENT
        )
