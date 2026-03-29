"""
Course instructor team management views.

Endpoints for managing the instructor team (primary instructors + TAs) on a course.
Primary instructors have full control; TAs get read-only access to student data.
"""

import logging

from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from purplex.users_app.permissions import IsCourseInstructor, IsPrimaryCourseInstructor
from purplex.users_app.repositories.user_repository import UserRepository

from ..serializers import CourseInstructorCreateSerializer, CourseInstructorSerializer
from ..services.course_service import CourseService

logger = logging.getLogger(__name__)


class CourseTeamListCreateView(APIView):
    """
    GET: List course instructors/TAs (any instructor role).
    POST: Add instructor/TA (primary only).
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsPrimaryCourseInstructor()]
        return [IsCourseInstructor()]

    def get(self, request, course_id):
        """List all instructors and TAs for a course."""
        course = CourseService.get_course_by_id(course_id)
        if not course:
            return Response(
                {"error": "Course not found", "code": "course_not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        self.check_object_permissions(request, course)

        instructors = CourseService.get_course_instructors(course)
        serializer = CourseInstructorSerializer(instructors, many=True)
        return Response(serializer.data)

    def post(self, request, course_id):
        """Add an instructor or TA to a course."""
        course = CourseService.get_course_by_id(course_id)
        if not course:
            return Response(
                {"error": "Course not found", "code": "course_not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        self.check_object_permissions(request, course)

        serializer = CourseInstructorCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        role = serializer.validated_data["role"]
        user = UserRepository.get_by_email(serializer.validated_data["email"])

        if not user:
            return Response(
                {"error": "User not found", "code": "user_not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            ci = CourseService.add_course_instructor(
                course=course, user=user, role=role, added_by=request.user
            )
        except IntegrityError:
            return Response(
                {
                    "error": "User is already an instructor on this course",
                    "code": "already_instructor",
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            CourseInstructorSerializer(ci).data, status=status.HTTP_201_CREATED
        )


class CourseTeamDetailView(APIView):
    """
    PATCH: Change an instructor's role (primary only).
    DELETE: Remove an instructor/TA (primary only).
    """

    permission_classes = [IsPrimaryCourseInstructor]

    def patch(self, request, course_id, user_id):
        """Change an instructor's role on a course."""
        course = CourseService.get_course_by_id(course_id)
        if not course:
            return Response(
                {"error": "Course not found", "code": "course_not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        self.check_object_permissions(request, course)

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
        course = CourseService.get_course_by_id(course_id)
        if not course:
            return Response(
                {"error": "Course not found", "code": "course_not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        self.check_object_permissions(request, course)

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
