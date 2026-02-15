from django.urls import path

from .course_views import (  # Admin course views; Instructor course views; Student course views
    AdminAvailableProblemSetsView,
    AdminCourseAvailableProblemSetsView,
    AdminCourseDetailView,
    AdminCourseListCreateView,
    AdminCourseProblemSetsView,
    AdminCourseStudentsView,
    AdminInstructorsListView,
    CourseEnrollView,
    CourseLookupView,
    InstructorCourseAvailableProblemSetsView,
    InstructorCourseDetailView,
    InstructorCourseListView,
    InstructorCourseProblemSetOrderView,
    InstructorCourseProgressView,
    InstructorCourseStudentsView,
    StudentCourseDetailView,
    StudentCourseProgressView,
    StudentEnrolledCoursesView,
)

# Admin views
from .views.admin_views import (
    AdminCategoryView,
    AdminProblemDetailView,
    AdminProblemListView,
    AdminProblemSetDetailView,
    AdminProblemSetListView,
    AdminSubmissionDetailView,
    AdminSubmissionListView,
    AdminTestCaseView,
    AdminTestProblemView,
)

# Hint system views
from .views.hint_views import (
    AdminProblemHintView,
    ProblemHintAvailabilityView,
    ProblemHintDetailView,
)

# Instructor analytics views
from .views.instructor_analytics_views import (
    InstructorCourseAnalyticsView,
    InstructorCourseExportView,
    InstructorProblemAnalyticsView,
    InstructorProblemExportView,
    InstructorProblemSetActivityView,
    InstructorProblemSetExportView,
    InstructorStudentDetailView,
    InstructorStudentListView,
)

# Instructor Content Management views
from .views.instructor_content_views import (
    InstructorCourseCreateView,
    InstructorCourseProblemSetManageView,
    InstructorProblemDetailView,
    InstructorProblemListView,
    InstructorProblemSetDetailView,
    InstructorProblemSetListView,
    InstructorTestProblemView,
)

# Instructor FERPA-compliant views
from .views.instructor_views import (
    InstructorCourseProblemSetsView,
    InstructorCourseSubmissionsView,
)

# Probe views for Probeable Code problems
from .views.probe_views import (
    ProbeHistoryView,
    ProbeOracleView,
    ProbeStatusView,
    RefuteTestView,
)

# Progress tracking views
from .views.progress_views import (
    LastSubmissionView,
    ProblemSetProgressView,
    UserProgressView,
)

# Research export views
from .views.research_views import ProgressHistoryExportView, ResearchDataExportView

# SSE views for real-time updates
from .views.sse import CleanBatchSSEView, CleanTaskSSEView

# Student-facing views
from .views.student_views import (
    CategoryListView,
    ProblemDetailView,
    ProblemListView,
    ProblemSetDetailView,
    ProblemSetListView,
)

# Submission views
from .views.submission_views import (
    ActivitySubmissionView,
    ActivityTypesView,
    SubmissionHistoryView,
)

urlpatterns = [
    # Public/Student endpoints
    path("problems/", ProblemListView.as_view(), name="problem_list"),
    path("problems/<slug:slug>/", ProblemDetailView.as_view(), name="problem_detail"),
    path("problem-sets/", ProblemSetListView.as_view(), name="problem_set_list"),
    path(
        "problem-sets/<slug:slug>/",
        ProblemSetDetailView.as_view(),
        name="problem_set_detail",
    ),
    path("categories/", CategoryListView.as_view(), name="category_list"),
    path(
        "submit/", ActivitySubmissionView.as_view(), name="submit_activity"
    ),  # Unified submission endpoint
    path(
        "activity-types/", ActivityTypesView.as_view(), name="activity_types"
    ),  # List registered types
    path(
        "submissions/history/<slug:problem_slug>/",
        SubmissionHistoryView.as_view(),
        name="submission_history",
    ),
    # SSE endpoints for real-time updates
    path("tasks/<str:task_id>/stream/", CleanTaskSSEView.as_view(), name="task_stream"),
    path("tasks/batch/stream/", CleanBatchSSEView.as_view(), name="task_batch_stream"),
    # Progress endpoints
    path("progress/", UserProgressView.as_view(), name="user_progress_all"),
    path(
        "progress/<slug:problem_slug>/",
        UserProgressView.as_view(),
        name="user_progress_problem",
    ),
    path(
        "problem-sets/<slug:slug>/progress/",
        ProblemSetProgressView.as_view(),
        name="problem_set_progress",
    ),
    path(
        "last-submission/<slug:problem_slug>/",
        LastSubmissionView.as_view(),
        name="last_submission",
    ),
    # Hint endpoints
    path(
        "problems/<slug:slug>/hints/",
        ProblemHintAvailabilityView.as_view(),
        name="problem_hint_availability",
    ),
    path(
        "problems/<slug:slug>/hints/<str:hint_type>/",
        ProblemHintDetailView.as_view(),
        name="problem_hint_detail",
    ),
    # Probe endpoints (Probeable Code problems)
    path("problems/<slug:slug>/probe/", ProbeOracleView.as_view(), name="probe_oracle"),
    path(
        "problems/<slug:slug>/probe/status/",
        ProbeStatusView.as_view(),
        name="probe_status",
    ),
    path(
        "problems/<slug:slug>/probe/history/",
        ProbeHistoryView.as_view(),
        name="probe_history",
    ),
    # Refute test endpoint (counterexample testing)
    path(
        "problems/<slug:slug>/test-counterexample/",
        RefuteTestView.as_view(),
        name="refute_test",
    ),
    # Admin endpoints - Problems
    path("admin/problems/", AdminProblemListView.as_view(), name="admin_problem_list"),
    path(
        "admin/problems/<slug:slug>/",
        AdminProblemDetailView.as_view(),
        name="admin_problem_detail",
    ),
    path(
        "admin/problems/<slug:slug>/hints/",
        AdminProblemHintView.as_view(),
        name="admin_problem_hints",
    ),
    path(
        "admin/test-problem/", AdminTestProblemView.as_view(), name="admin_test_problem"
    ),
    # Admin endpoints - Test Cases
    path(
        "admin/problems/<slug:problem_slug>/test-cases/",
        AdminTestCaseView.as_view(),
        name="admin_test_case_create",
    ),
    path(
        "admin/problems/<slug:problem_slug>/test-cases/<int:test_case_id>/",
        AdminTestCaseView.as_view(),
        name="admin_test_case_detail",
    ),
    # Admin endpoints - Problem Sets
    path(
        "admin/problem-sets/",
        AdminProblemSetListView.as_view(),
        name="admin_problem_set_list",
    ),
    path(
        "admin/problem-sets/available/",
        AdminAvailableProblemSetsView.as_view(),
        name="admin_available_problemsets",
    ),
    path(
        "admin/problem-sets/<slug:slug>/",
        AdminProblemSetDetailView.as_view(),
        name="admin_problem_set_detail",
    ),
    # Admin endpoints - Categories
    path("admin/categories/", AdminCategoryView.as_view(), name="admin_category_list"),
    path(
        "admin/categories/<int:pk>/",
        AdminCategoryView.as_view(),
        name="admin_category_detail",
    ),
    # Admin endpoints - Submissions
    path(
        "admin/submissions/",
        AdminSubmissionListView.as_view(),
        name="admin_submission_list",
    ),
    path(
        "admin/submissions/export/",
        AdminSubmissionListView.as_view(),
        name="admin_submission_export",
    ),
    path(
        "admin/submissions/<str:submission_id>/",
        AdminSubmissionDetailView.as_view(),
        name="admin_submission_detail",
    ),
    # Research data export endpoints
    path(
        "admin/research/export/",
        ResearchDataExportView.as_view(),
        name="research_export",
    ),
    path(
        "admin/research/progress-history/",
        ProgressHistoryExportView.as_view(),
        name="progress_history_export",
    ),
    # Admin Course Management
    path(
        "admin/instructors/",
        AdminInstructorsListView.as_view(),
        name="admin_instructors_list",
    ),
    path(
        "admin/courses/", AdminCourseListCreateView.as_view(), name="admin_course_list"
    ),
    path(
        "admin/courses/<str:course_id>/",
        AdminCourseDetailView.as_view(),
        name="admin_course_detail",
    ),
    path(
        "admin/courses/<str:course_id>/problem-sets/",
        AdminCourseProblemSetsView.as_view(),
        name="admin_course_problemsets",
    ),
    path(
        "admin/courses/<str:course_id>/problem-sets/<str:problem_set_slug>/",
        AdminCourseProblemSetsView.as_view(),
        name="admin_course_problemset_detail",
    ),
    path(
        "admin/courses/<str:course_id>/available-problem-sets/",
        AdminCourseAvailableProblemSetsView.as_view(),
        name="admin_course_available_problemsets",
    ),
    path(
        "admin/courses/<str:course_id>/students/",
        AdminCourseStudentsView.as_view(),
        name="admin_course_students",
    ),
    path(
        "admin/courses/<str:course_id>/students/<int:user_id>/",
        AdminCourseStudentsView.as_view(),
        name="admin_course_student_remove",
    ),
    # Instructor Course Views
    path(
        "instructor/courses/",
        InstructorCourseListView.as_view(),
        name="instructor_course_list",
    ),
    # IMPORTANT: create must come BEFORE <str:course_id> to avoid matching "create" as a course_id
    path(
        "instructor/courses/create/",
        InstructorCourseCreateView.as_view(),
        name="instructor_course_create",
    ),
    path(
        "instructor/courses/<str:course_id>/",
        InstructorCourseDetailView.as_view(),
        name="instructor_course_detail",
    ),
    path(
        "instructor/courses/<str:course_id>/students/",
        InstructorCourseStudentsView.as_view(),
        name="instructor_course_students",
    ),
    path(
        "instructor/courses/<str:course_id>/progress/",
        InstructorCourseProgressView.as_view(),
        name="instructor_course_progress",
    ),
    path(
        "instructor/courses/<str:course_id>/problem-sets/",
        InstructorCourseProblemSetsView.as_view(),
        name="instructor_course_problemsets",
    ),
    path(
        "instructor/courses/<str:course_id>/problem-sets/reorder/",
        InstructorCourseProblemSetOrderView.as_view(),
        name="instructor_course_reorder",
    ),
    path(
        "instructor/courses/<str:course_id>/available-problem-sets/",
        InstructorCourseAvailableProblemSetsView.as_view(),
        name="instructor_course_available_problemsets",
    ),
    path(
        "instructor/courses/<str:course_id>/submissions/",
        InstructorCourseSubmissionsView.as_view(),
        name="instructor_course_submissions",
    ),
    # Instructor Analytics Views
    path(
        "instructor/courses/<str:course_id>/analytics/",
        InstructorCourseAnalyticsView.as_view(),
        name="instructor_course_analytics",
    ),
    path(
        "instructor/courses/<str:course_id>/analytics/students/",
        InstructorStudentListView.as_view(),
        name="instructor_student_list",
    ),
    path(
        "instructor/courses/<str:course_id>/analytics/students/<int:user_id>/",
        InstructorStudentDetailView.as_view(),
        name="instructor_student_detail",
    ),
    path(
        "instructor/courses/<str:course_id>/analytics/problems/<slug:problem_slug>/",
        InstructorProblemAnalyticsView.as_view(),
        name="instructor_problem_analytics",
    ),
    path(
        "instructor/courses/<str:course_id>/export/",
        InstructorCourseExportView.as_view(),
        name="instructor_course_export",
    ),
    path(
        "instructor/courses/<str:course_id>/problem-sets/<slug:problem_set_slug>/activity/",
        InstructorProblemSetActivityView.as_view(),
        name="instructor_problem_set_activity",
    ),
    path(
        "instructor/courses/<str:course_id>/problem-sets/<slug:problem_set_slug>/export/",
        InstructorProblemSetExportView.as_view(),
        name="instructor_problem_set_export",
    ),
    path(
        "instructor/courses/<str:course_id>/problems/<slug:problem_slug>/export/",
        InstructorProblemExportView.as_view(),
        name="instructor_problem_export",
    ),
    # Instructor Content Management
    path(
        "instructor/problems/",
        InstructorProblemListView.as_view(),
        name="instructor_problem_list",
    ),
    path(
        "instructor/problems/<slug:slug>/",
        InstructorProblemDetailView.as_view(),
        name="instructor_problem_detail",
    ),
    path(
        "instructor/test-problem/",
        InstructorTestProblemView.as_view(),
        name="instructor_test_problem",
    ),
    path(
        "instructor/problem-sets/",
        InstructorProblemSetListView.as_view(),
        name="instructor_problem_set_list",
    ),
    path(
        "instructor/problem-sets/<slug:slug>/",
        InstructorProblemSetDetailView.as_view(),
        name="instructor_problem_set_detail",
    ),
    path(
        "instructor/courses/<str:course_id>/problem-sets/manage/",
        InstructorCourseProblemSetManageView.as_view(),
        name="instructor_course_problemset_manage",
    ),
    path(
        "instructor/courses/<str:course_id>/problem-sets/manage/<slug:problem_set_slug>/",
        InstructorCourseProblemSetManageView.as_view(),
        name="instructor_course_problemset_remove",
    ),
    # PATCH/DELETE by membership ID (for frontend compatibility)
    path(
        "instructor/courses/<str:course_id>/problem-sets/<int:membership_id>/",
        InstructorCourseProblemSetManageView.as_view(),
        name="instructor_course_problemset_by_id",
    ),
    # Student Course Views
    path(
        "courses/enrolled/",
        StudentEnrolledCoursesView.as_view(),
        name="student_enrolled_courses",
    ),
    path("courses/lookup/", CourseLookupView.as_view(), name="course_lookup"),
    path("courses/enroll/", CourseEnrollView.as_view(), name="course_enroll"),
    path(
        "courses/<str:course_id>/",
        StudentCourseDetailView.as_view(),
        name="student_course_detail",
    ),
    path(
        "courses/<str:course_id>/progress/",
        StudentCourseProgressView.as_view(),
        name="student_course_progress",
    ),
]
