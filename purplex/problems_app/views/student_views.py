"""Student-facing views for problems and problem sets."""

import logging
from django.shortcuts import get_object_or_404
from django.db.models import Count
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from ..models import Problem, ProblemSet, ProblemCategory
from ..serializers import (
    ProblemSerializer, ProblemSetSerializer, ProblemCategorySerializer,
    TestCaseSerializer, ProblemListSerializer, ProblemSetListSerializer
)
from purplex.users_app.permissions import IsAuthenticated

logger = logging.getLogger(__name__)


class ProblemListView(APIView):
    """List all active problems for students."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Optimized query - include all fields needed by ProblemListSerializer
        problems = Problem.objects.filter(is_active=True).prefetch_related(
            'categories',
            'test_cases',
            'problem_sets'
        ).only(
            'slug', 'title', 'description', 'difficulty', 'problem_type', 
            'function_name', 'tags', 'is_active', 'created_at'
        )
        serializer = ProblemListSerializer(problems, many=True)
        return Response(serializer.data)


class ProblemDetailView(APIView):
    """Get detailed view of a specific problem for students."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, slug):
        problem = get_object_or_404(Problem, slug=slug, is_active=True)
        serializer = ProblemSerializer(problem)
        data = serializer.data
        
        # Only include non-hidden test cases for students
        visible_test_cases = problem.test_cases.filter(is_hidden=False)
        data['test_cases'] = TestCaseSerializer(visible_test_cases, many=True).data
        
        return Response(data)


class ProblemSetListView(APIView):
    """List all active problem sets for students."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Enhanced query with performance optimizations
        problem_sets = ProblemSet.objects.filter(is_public=True).prefetch_related(
            'problems',
            'problems__categories'
        ).annotate(
            problems_count=Count('problems')
        ).order_by('-created_at')
        
        serializer = ProblemSetListSerializer(problem_sets, many=True)
        return Response(serializer.data)


class ProblemSetDetailView(APIView):
    """Get detailed view of a specific problem set for students."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, slug):
        # Enhanced query - get problem set with all related data
        problem_set = get_object_or_404(
            ProblemSet.objects.prefetch_related(
                'problems__categories',
                'problems__test_cases'
            ).select_related(),
            slug=slug,
            is_public=True
        )
        
        serializer = ProblemSetSerializer(problem_set)
        data = serializer.data
        
        # Get problems with ordering and include only visible test cases
        ordered_problems = []
        memberships = problem_set.problemsetmembership_set.select_related('problem').order_by('order')
        
        for membership in memberships:
            problem = membership.problem
            if problem.is_active:  # Only include active problems
                problem_data = ProblemSerializer(problem).data
                # Only include non-hidden test cases
                visible_test_cases = problem.test_cases.filter(is_hidden=False)
                problem_data['test_cases'] = TestCaseSerializer(visible_test_cases, many=True).data
                ordered_problems.append(problem_data)
        
        data['problems'] = ordered_problems
        return Response(data)


class CategoryListView(APIView):
    """List all problem categories."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        categories = ProblemCategory.objects.all().order_by('name')
        serializer = ProblemCategorySerializer(categories, many=True)
        return Response(serializer.data)