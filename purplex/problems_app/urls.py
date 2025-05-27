from django.urls import path
from .views import (
    # Public/Student views
    ProblemListView, ProblemDetailView, ProblemSetListView, ProblemSetDetailView,
    CategoryListView, TestSolutionView,
    
    # Admin views
    AdminProblemListView, AdminProblemDetailView, AdminTestProblemView,
    AdminGenerateTestCasesView, AdminTestCaseView, AdminProblemSetListView,
    AdminProblemSetDetailView, AdminCategoryView
)

urlpatterns = [
    # Public/Student endpoints
    path('problems/', ProblemListView.as_view(), name='problem_list'),
    path('problems/<slug:slug>/', ProblemDetailView.as_view(), name='problem_detail'),
    path('problem-sets/', ProblemSetListView.as_view(), name='problem_set_list'),
    path('problem-sets/<slug:slug>/', ProblemSetDetailView.as_view(), name='problem_set_detail'),
    path('categories/', CategoryListView.as_view(), name='category_list'),
    path('test-solution/', TestSolutionView.as_view(), name='test_solution'),
    
    # Admin endpoints - Problems
    path('admin/problems/', AdminProblemListView.as_view(), name='admin_problem_list'),
    path('admin/problems/<slug:slug>/', AdminProblemDetailView.as_view(), name='admin_problem_detail'),
    path('admin/test-problem/', AdminTestProblemView.as_view(), name='admin_test_problem'),
    path('admin/generate-test-cases/', AdminGenerateTestCasesView.as_view(), name='admin_generate_test_cases'),
    
    # Admin endpoints - Test Cases
    path('admin/problems/<slug:problem_slug>/test-cases/', AdminTestCaseView.as_view(), name='admin_test_case_create'),
    path('admin/problems/<slug:problem_slug>/test-cases/<int:test_case_id>/', AdminTestCaseView.as_view(), name='admin_test_case_detail'),
    
    # Admin endpoints - Problem Sets
    path('admin/problem-sets/', AdminProblemSetListView.as_view(), name='admin_problem_set_list'),
    path('admin/problem-sets/<slug:slug>/', AdminProblemSetDetailView.as_view(), name='admin_problem_set_detail'),
    
    # Admin endpoints - Categories
    path('admin/categories/', AdminCategoryView.as_view(), name='admin_category_list'),
    path('admin/categories/<int:pk>/', AdminCategoryView.as_view(), name='admin_category_detail'),
]