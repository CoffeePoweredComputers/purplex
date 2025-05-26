from django.urls import path
from .views import (
    ProblemListView, ProblemSetListView, GetProblemSet,
    AdminProblemView, AdminProblemSetView
)

urlpatterns = [
    # Regular user endpoints
    path('problems/', ProblemListView.as_view(), name='problem_list'),
    path('problem-sets/', ProblemSetListView.as_view(), name='problem_set_list'),
    path('problem-set/<str:sid>/', GetProblemSet.as_view(), name='get_problem_set'),
    
    # Admin endpoints
    path('admin/problems/', AdminProblemView.as_view(), name='admin_problem_create'),
    path('admin/problem/<str:qid>/', AdminProblemView.as_view(), name='admin_problem_detail'),
    path('admin/problem-sets/', AdminProblemSetView.as_view(), name='admin_problem_set_create'),
    path('admin/problem-set/<str:sid>/', AdminProblemSetView.as_view(), name='admin_problem_set_detail'),
]