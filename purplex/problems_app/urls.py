from django.urls import path

# Student-facing views
from .views.student_views import (
    ProblemListView, ProblemDetailView, ProblemSetListView, 
    ProblemSetDetailView, CategoryListView
)

# Submission views
from .views.submission_views import (
    TestSolutionView, SubmitSolutionView, EiPLSubmissionView
)

# SSE views for real-time updates
from .views.sse import CleanTaskSSEView, CleanBatchSSEView

# Progress tracking views
from .views.progress_views import (
    UserProgressView, ProblemSetProgressView, UserProgressSummaryView, LastSubmissionView
)

# Admin views
from .views.admin_views import (
    AdminProblemListView, AdminProblemDetailView, AdminTestProblemView,
    AdminTestCaseView, AdminProblemSetListView, AdminProblemSetDetailView,
    AdminCategoryView, AdminSubmissionListView, AdminSubmissionDetailView
)

# Hint system views
from .views.hint_views import (
    ProblemHintAvailabilityView, ProblemHintDetailView, AdminProblemHintView
)
from .course_views import (
    # Admin course views
    AdminCourseListCreateView, AdminCourseDetailView, AdminCourseProblemSetView,
    AdminCourseProblemSetsView, AdminAvailableProblemSetsView, AdminCourseStudentsView,
    
    # Instructor course views
    InstructorCourseListView, InstructorCourseDetailView, InstructorCourseStudentsView,
    InstructorCourseProgressView, InstructorCourseProblemSetOrderView,
    
    # Student course views
    StudentEnrolledCoursesView, CourseLookupView, CourseEnrollView,
    StudentCourseDetailView, StudentCourseProgressView
)

urlpatterns = [
    # Public/Student endpoints
    path('problems/', ProblemListView.as_view(), name='problem_list'),
    path('problems/<slug:slug>/', ProblemDetailView.as_view(), name='problem_detail'),
    path('problem-sets/', ProblemSetListView.as_view(), name='problem_set_list'),
    path('problem-sets/<slug:slug>/', ProblemSetDetailView.as_view(), name='problem_set_detail'),
    path('categories/', CategoryListView.as_view(), name='category_list'),
    path('test-solution/', TestSolutionView.as_view(), name='test_solution'),
    path('submit-solution/', SubmitSolutionView.as_view(), name='submit_solution'),
    path('submit-eipl/', EiPLSubmissionView.as_view(), name='submit_eipl'),
    
    # SSE endpoints for real-time updates
    path('tasks/<str:task_id>/stream/', CleanTaskSSEView.as_view(), name='task_stream'),
    path('tasks/batch/stream/', CleanBatchSSEView.as_view(), name='task_batch_stream'),
    
    # Progress endpoints
    path('progress/', UserProgressView.as_view(), name='user_progress_all'),
    path('progress/<slug:problem_slug>/', UserProgressView.as_view(), name='user_progress_problem'),
    path('problem-sets/<slug:slug>/progress/', ProblemSetProgressView.as_view(), name='problem_set_progress'),
    path('last-submission/<slug:problem_slug>/', LastSubmissionView.as_view(), name='last_submission'),
    
    # Hint endpoints
    path('problems/<slug:slug>/hints/', ProblemHintAvailabilityView.as_view(), name='problem_hint_availability'),
    path('problems/<slug:slug>/hints/<str:hint_type>/', ProblemHintDetailView.as_view(), name='problem_hint_detail'),
    
    # Admin endpoints - Problems
    path('admin/problems/', AdminProblemListView.as_view(), name='admin_problem_list'),
    path('admin/problems/<slug:slug>/', AdminProblemDetailView.as_view(), name='admin_problem_detail'),
    path('admin/problems/<slug:slug>/hints/', AdminProblemHintView.as_view(), name='admin_problem_hints'),
    path('admin/test-problem/', AdminTestProblemView.as_view(), name='admin_test_problem'),
    
    # Admin endpoints - Test Cases
    path('admin/problems/<slug:problem_slug>/test-cases/', AdminTestCaseView.as_view(), name='admin_test_case_create'),
    path('admin/problems/<slug:problem_slug>/test-cases/<int:test_case_id>/', AdminTestCaseView.as_view(), name='admin_test_case_detail'),
    
    # Admin endpoints - Problem Sets
    path('admin/problem-sets/', AdminProblemSetListView.as_view(), name='admin_problem_set_list'),
    path('admin/problem-sets/available/', AdminAvailableProblemSetsView.as_view(), name='admin_available_problemsets'),
    path('admin/problem-sets/<slug:slug>/', AdminProblemSetDetailView.as_view(), name='admin_problem_set_detail'),
    
    # Admin endpoints - Categories
    path('admin/categories/', AdminCategoryView.as_view(), name='admin_category_list'),
    path('admin/categories/<int:pk>/', AdminCategoryView.as_view(), name='admin_category_detail'),

    # Admin endpoints - Submissions
    path('admin/submissions/', AdminSubmissionListView.as_view(), name='admin_submission_list'),
    path('admin/submissions/export/', AdminSubmissionListView.as_view(), name='admin_submission_export'),
    path('admin/submissions/<str:submission_id>/', AdminSubmissionDetailView.as_view(), name='admin_submission_detail'),

    # Admin Course Management
    path('admin/courses/', AdminCourseListCreateView.as_view(), name='admin_course_list'),
    path('admin/courses/<str:course_id>/', AdminCourseDetailView.as_view(), name='admin_course_detail'),
    path('admin/courses/<str:course_id>/problem-sets/', AdminCourseProblemSetsView.as_view(), name='admin_course_problemsets'),
    path('admin/courses/<str:course_id>/problem-sets/<str:problem_set_slug>/', AdminCourseProblemSetsView.as_view(), name='admin_course_problemset_detail'),
    path('admin/courses/<str:course_id>/students/', AdminCourseStudentsView.as_view(), name='admin_course_students'),
    path('admin/courses/<str:course_id>/students/<int:user_id>/', AdminCourseStudentsView.as_view(), name='admin_course_student_remove'),
    
    # Instructor Course Views
    path('instructor/courses/', InstructorCourseListView.as_view(), name='instructor_course_list'),
    path('instructor/courses/<str:course_id>/', InstructorCourseDetailView.as_view(), name='instructor_course_detail'),
    path('instructor/courses/<str:course_id>/students/', InstructorCourseStudentsView.as_view(), name='instructor_course_students'),
    path('instructor/courses/<str:course_id>/progress/', InstructorCourseProgressView.as_view(), name='instructor_course_progress'),
    path('instructor/courses/<str:course_id>/problem-sets/order/', InstructorCourseProblemSetOrderView.as_view(), name='instructor_course_reorder'),
    
    # Student Course Views
    path('courses/enrolled/', StudentEnrolledCoursesView.as_view(), name='student_enrolled_courses'),
    path('courses/lookup/', CourseLookupView.as_view(), name='course_lookup'),
    path('courses/enroll/', CourseEnrollView.as_view(), name='course_enroll'),
    path('courses/<str:course_id>/', StudentCourseDetailView.as_view(), name='student_course_detail'),
    path('courses/<str:course_id>/progress/', StudentCourseProgressView.as_view(), name='student_course_progress'),
]