from django.urls import path
from .views import (
    # Public/Student views
    ProblemListView, ProblemDetailView, ProblemSetListView, ProblemSetDetailView,
    CategoryListView, TestSolutionView, SubmitSolutionView, EiPLSubmissionView,
    
    # Progress views
    UserProgressView, ProblemSetProgressView, UserProgressSummaryView,
    
    # Admin views
    AdminProblemListView, AdminProblemDetailView, AdminTestProblemView,
    AdminTestCaseView, AdminProblemSetListView,
    AdminProblemSetDetailView, AdminCategoryView
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
    
    # Progress endpoints
    path('progress/', UserProgressView.as_view(), name='user_progress_all'),
    path('progress/<slug:problem_slug>/', UserProgressView.as_view(), name='user_progress_problem'),
    path('progress-summary/', UserProgressSummaryView.as_view(), name='user_progress_summary'),
    path('problem-sets/<slug:slug>/progress/', ProblemSetProgressView.as_view(), name='problem_set_progress'),
    
    # Admin endpoints - Problems
    path('admin/problems/', AdminProblemListView.as_view(), name='admin_problem_list'),
    path('admin/problems/<slug:slug>/', AdminProblemDetailView.as_view(), name='admin_problem_detail'),
    path('admin/test-problem/', AdminTestProblemView.as_view(), name='admin_test_problem'),
    
    # Admin endpoints - Test Cases
    path('admin/problems/<slug:problem_slug>/test-cases/', AdminTestCaseView.as_view(), name='admin_test_case_create'),
    path('admin/problems/<slug:problem_slug>/test-cases/<int:test_case_id>/', AdminTestCaseView.as_view(), name='admin_test_case_detail'),
    
    # Admin endpoints - Problem Sets
    path('admin/problem-sets/', AdminProblemSetListView.as_view(), name='admin_problem_set_list'),
    path('admin/problem-sets/<slug:slug>/', AdminProblemSetDetailView.as_view(), name='admin_problem_set_detail'),
    
    # Admin endpoints - Categories
    path('admin/categories/', AdminCategoryView.as_view(), name='admin_category_list'),
    path('admin/categories/<int:pk>/', AdminCategoryView.as_view(), name='admin_category_detail'),
    
    # Admin Course Management
    path('admin/courses/', AdminCourseListCreateView.as_view(), name='admin_course_list'),
    path('admin/courses/<str:course_id>/', AdminCourseDetailView.as_view(), name='admin_course_detail'),
    path('admin/courses/<str:course_id>/problem-sets/', AdminCourseProblemSetsView.as_view(), name='admin_course_problemsets'),
    path('admin/courses/<str:course_id>/problem-sets/<str:problem_set_slug>/', AdminCourseProblemSetsView.as_view(), name='admin_course_problemset_detail'),
    path('admin/courses/<str:course_id>/students/', AdminCourseStudentsView.as_view(), name='admin_course_students'),
    path('admin/courses/<str:course_id>/students/<int:user_id>/', AdminCourseStudentsView.as_view(), name='admin_course_student_remove'),
    path('admin/problem-sets/available/', AdminAvailableProblemSetsView.as_view(), name='admin_available_problemsets'),
    
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