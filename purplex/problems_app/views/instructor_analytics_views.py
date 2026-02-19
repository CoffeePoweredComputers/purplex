"""
API views for instructor analytics.
"""

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from purplex.problems_app.repositories import CourseEnrollmentRepository
from purplex.problems_app.repositories.course_repository import CourseRepository
from purplex.problems_app.repositories.problem_repository import ProblemRepository
from purplex.problems_app.repositories.problem_set_repository import (
    ProblemSetRepository,
)
from purplex.problems_app.services.course_export_service import CourseExportService
from purplex.problems_app.services.instructor_analytics_service import (
    InstructorAnalyticsService,
)
from purplex.users_app.permissions import IsCourseInstructor
from purplex.users_app.repositories.user_repository import UserRepository


class InstructorCourseAnalyticsView(APIView):
    """
    Get analytics overview for a course.

    Requires: User must be the course instructor
    """

    permission_classes = [IsCourseInstructor]

    def get(self, request, course_id):
        """Get course analytics overview."""
        course = CourseRepository.get_course_by_id(course_id)
        if not course:
            return Response(
                {"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Verify instructor permission
        self.check_object_permissions(request, course)

        # Get analytics
        analytics = InstructorAnalyticsService.get_course_overview(course)

        return Response(analytics, status=status.HTTP_200_OK)


class InstructorProblemSetActivityView(APIView):
    """
    Get activity data for a specific problem set in a course.

    Used by the instructor course overview when filtering by problem set.
    Returns daily submission counts for the last 7 days.

    Requires: User must be the course instructor
    """

    permission_classes = [IsCourseInstructor]

    def get(self, request, course_id, problem_set_slug):
        """Get problem set activity data."""
        course = CourseRepository.get_course_by_id(course_id)
        if not course:
            return Response(
                {"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Verify instructor permission
        self.check_object_permissions(request, course)

        # Get enrolled student IDs
        student_ids = CourseEnrollmentRepository.get_active_student_ids(course)

        # Get activity data for the problem set
        try:
            activity_data = InstructorAnalyticsService.get_problem_set_activity(
                course=course,
                problem_set_slug=problem_set_slug,
                student_ids=student_ids,
            )
        except Exception:
            return Response(
                {"error": "Problem set not found"}, status=status.HTTP_404_NOT_FOUND
            )

        return Response(activity_data, status=status.HTTP_200_OK)


class InstructorStudentListView(APIView):
    """
    Get list of students in a course with progress metrics.

    Query Parameters:
        sort_by: Field to sort by (progress, score, activity, name)
        order: Sort order (asc or desc)
    """

    permission_classes = [IsCourseInstructor]

    def get(self, request, course_id):
        """Get student list with metrics."""
        course = CourseRepository.get_course_by_id(course_id)
        if not course:
            return Response(
                {"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Verify instructor permission
        self.check_object_permissions(request, course)

        # Get query parameters
        sort_by = request.query_params.get("sort_by", "progress")
        order = request.query_params.get("order", "desc")

        # Get student list
        students = InstructorAnalyticsService.get_student_list(
            course=course, sort_by=sort_by, order=order
        )

        return Response(
            {
                "course_id": course.course_id,
                "students": students,
                "total_students": len(students),
            },
            status=status.HTTP_200_OK,
        )


class InstructorStudentDetailView(APIView):
    """
    Get detailed analytics for a specific student.
    """

    permission_classes = [IsCourseInstructor]

    def get(self, request, course_id, user_id):
        """Get student detail analytics."""
        course = CourseRepository.get_course_by_id(course_id)
        if not course:
            return Response(
                {"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND
            )

        user = UserRepository.get_by_id(user_id)
        if not user:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Verify instructor permission
        self.check_object_permissions(request, course)

        # Get student analytics
        analytics = InstructorAnalyticsService.get_student_detail(
            course=course, user=user
        )

        return Response(analytics, status=status.HTTP_200_OK)


class InstructorProblemAnalyticsView(APIView):
    """
    Get analytics for a specific problem.
    """

    permission_classes = [IsCourseInstructor]

    def get(self, request, course_id, problem_slug):
        """Get problem analytics."""
        course = CourseRepository.get_course_by_id(course_id)
        if not course:
            return Response(
                {"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND
            )

        problem = ProblemRepository.get_problem_by_slug(problem_slug)
        if not problem:
            return Response(
                {"error": "Problem not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Verify instructor permission
        self.check_object_permissions(request, course)

        # Get problem analytics
        analytics = InstructorAnalyticsService.get_problem_analytics(
            course=course, problem=problem
        )

        return Response(analytics, status=status.HTTP_200_OK)


class InstructorCourseExportView(APIView):
    """
    Export course progress to CSV.

    Query Parameters:
        include_inactive: Include inactive students (default: false)
    """

    permission_classes = [IsCourseInstructor]

    def get(self, request, course_id):
        """Export course progress."""
        course = CourseRepository.get_course_by_id(course_id)
        if not course:
            return Response(
                {"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Verify instructor permission
        self.check_object_permissions(request, course)

        # Get parameters
        include_inactive = (
            request.query_params.get("include_inactive", "false").lower() == "true"
        )

        # Generate CSV
        csv_data = CourseExportService.export_course_progress(
            course=course, include_inactive=include_inactive
        )

        # Create response
        response = HttpResponse(csv_data, content_type="text/csv")
        filename = f"course_{course.course_id}_progress_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response


class InstructorProblemSetExportView(APIView):
    """
    Export problem set scores to CSV.

    Query Parameters:
        include_inactive: Include inactive students (default: false)
    """

    permission_classes = [IsCourseInstructor]

    def get(self, request, course_id, problem_set_slug):
        """Export problem set scores."""
        course = CourseRepository.get_course_by_id(course_id)
        if not course:
            return Response(
                {"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND
            )

        problem_set = ProblemSetRepository.get_problem_set_by_slug(problem_set_slug)
        if not problem_set:
            return Response(
                {"error": "Problem set not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Verify instructor permission
        self.check_object_permissions(request, course)

        # Get parameters
        include_inactive = (
            request.query_params.get("include_inactive", "false").lower() == "true"
        )

        # Generate CSV
        csv_data = CourseExportService.export_problem_set_scores(
            course=course, problem_set=problem_set, include_inactive=include_inactive
        )

        # Create response
        response = HttpResponse(csv_data, content_type="text/csv")
        filename = f"course_{course.course_id}_{problem_set.slug}_scores_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response


class InstructorProblemExportView(APIView):
    """
    Export individual problem scores to CSV.

    Query Parameters:
        include_inactive: Include inactive students (default: false)
    """

    permission_classes = [IsCourseInstructor]

    def get(self, request, course_id, problem_slug):
        """Export problem scores."""
        course = CourseRepository.get_course_by_id(course_id)
        if not course:
            return Response(
                {"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND
            )

        problem = ProblemRepository.get_problem_by_slug(problem_slug)
        if not problem:
            return Response(
                {"error": "Problem not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Verify instructor permission
        self.check_object_permissions(request, course)

        # Get parameters
        include_inactive = (
            request.query_params.get("include_inactive", "false").lower() == "true"
        )

        # Generate CSV
        csv_data = CourseExportService.export_problem_scores(
            course=course, problem=problem, include_inactive=include_inactive
        )

        # Create response
        response = HttpResponse(csv_data, content_type="text/csv")
        filename = f"course_{course.course_id}_{problem.slug}_scores_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response
