"""
Instructor views for FERPA-compliant access to course data.

These views ensure instructors can only see data from courses they teach.
All views use IsCourseInstructor permission for object-level access control.
"""

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from purplex.problems_app.repositories.course_repository import CourseRepository
from purplex.problems_app.services.course_service import CourseService
from purplex.submissions.repositories import SubmissionRepository
from purplex.users_app.permissions import IsCourseInstructor

logger = logging.getLogger(__name__)


class InstructorCourseProblemSetsView(APIView):
    """
    View problem sets assigned to an instructor's course.

    GET /api/instructor/courses/{course_id}/problem-sets/

    Returns problem sets with their order and required status.
    FERPA Compliant: Only returns data for courses the instructor teaches.
    """

    permission_classes = [IsCourseInstructor]

    def get(self, request, course_id):
        """Get all problem sets assigned to the instructor's course."""
        course = CourseRepository.get_course_by_id(course_id)
        if not course:
            return Response(
                {"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Verify instructor permission (IsCourseInstructor checks this)
        self.check_object_permissions(request, course)

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
                        "description": cps["problem_set"].get("description", ""),
                        "problems_count": cps["problem_set"]["problems_count"],
                    },
                    "order": cps["order"],
                    "is_required": cps["is_required"],
                }
            )

        return Response(response_data)


class InstructorCourseSubmissionsView(APIView):
    """
    View submissions from students enrolled in an instructor's course.

    GET /api/instructor/courses/{course_id}/submissions/

    Query Parameters:
        page: Page number (default: 1)
        page_size: Results per page (default: 25, max: 100)
        search: Search by student username or problem title
        type: Filter by submission type (code, eipl, mcq, etc.)
        status: Filter by completion status (incomplete, partial, complete)
        problem_set: Filter by problem set slug

    FERPA Compliant: Only returns submissions from students enrolled in the
    instructor's course. Instructors cannot see submissions from other courses.
    """

    permission_classes = [IsCourseInstructor]

    def get(self, request, course_id):
        """Get paginated submissions for the instructor's course."""
        course = CourseRepository.get_course_by_id(course_id)
        if not course:
            return Response(
                {"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Verify instructor permission
        self.check_object_permissions(request, course)

        # Get query parameters
        page = int(request.query_params.get("page", 1))
        page_size = min(int(request.query_params.get("page_size", 25)), 100)
        search = request.query_params.get("search", "")
        submission_type = request.query_params.get("type", "")
        status_filter = request.query_params.get("status", "")
        problem_set_filter = request.query_params.get("problem_set", "")

        # Get paginated submissions filtered by course
        # This is the FERPA-critical filter - only submissions from this course
        paginated_data = SubmissionRepository.get_paginated_submissions(
            page=page,
            page_size=page_size,
            search=search,
            submission_type=submission_type if submission_type else None,
            status_filter=status_filter if status_filter else None,
            course_filter=course.course_id,  # FERPA: Filter to this course only
            problem_set_filter=problem_set_filter if problem_set_filter else None,
        )

        paginated_submissions = paginated_data["submissions"]

        # Serialize data
        submissions_data = []
        for submission in paginated_submissions:
            submissions_data.append(
                {
                    "id": str(submission.submission_id),
                    "user": submission.user.username if submission.user else "Unknown",
                    "user_id": submission.user.id if submission.user else None,
                    "problem": submission.problem.title,
                    "problem_slug": submission.problem.slug,
                    "problem_set": (
                        submission.problem_set.title if submission.problem_set else None
                    ),
                    "problem_set_slug": (
                        submission.problem_set.slug if submission.problem_set else None
                    ),
                    "submission_type": submission.submission_type,
                    "score": submission.score,
                    "status": submission.completion_status,
                    "comprehension_level": submission.comprehension_level,
                    "is_correct": submission.is_correct,
                    "execution_status": submission.execution_status,
                    "submitted_at": submission.submitted_at.isoformat(),
                    "passed_all_tests": submission.passed_all_tests,
                    "execution_time_ms": submission.execution_time_ms,
                }
            )

        # Get filter metadata for this course's problem sets only
        course_problem_sets = CourseService.get_course_problem_sets(course)
        problem_set_options = [
            {"slug": cps["problem_set"]["slug"], "title": cps["problem_set"]["title"]}
            for cps in course_problem_sets
        ]

        filter_metadata = {
            "problem_sets": problem_set_options,
            "statuses": ["incomplete", "partial", "complete"],
            "types": ["code", "eipl", "mcq", "probeable_code", "refute", "debug_fix"],
        }

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
                "course": {
                    "course_id": course.course_id,
                    "name": course.name,
                },
            }
        )
