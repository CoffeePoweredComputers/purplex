"""Student-facing views for problems and problem sets."""

import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from ..serializers import (
    ProblemSerializer, ProblemSetSerializer, ProblemCategorySerializer,
    TestCaseSerializer, ProblemListSerializer, ProblemSetListSerializer
)
from ..services.student_service import StudentService
from purplex.users_app.permissions import IsAuthenticated

logger = logging.getLogger(__name__)


class ProblemListView(APIView):
    """List all active problems for students."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Use service layer for business logic
        problems = StudentService.get_active_problems(user=request.user)
        serializer = ProblemListSerializer(problems, many=True)
        return Response(serializer.data)


class ProblemDetailView(APIView):
    """Get detailed view of a specific problem for students."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, slug):
        # Use service layer
        problem = StudentService.get_problem_detail(slug)
        serializer = ProblemSerializer(problem)
        data = serializer.data
        
        # Get visible test cases through service
        visible_test_cases = StudentService.get_visible_test_cases(problem)
        data['test_cases'] = TestCaseSerializer(visible_test_cases, many=True).data
        
        return Response(data)


class ProblemSetListView(APIView):
    """List all active problem sets for students."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Use service layer
        problem_sets = StudentService.get_public_problem_sets()
        serializer = ProblemSetListSerializer(problem_sets, many=True)
        return Response(serializer.data)


class ProblemSetDetailView(APIView):
    """Get detailed view of a specific problem set for students."""
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        # Use service layer
        problem_set = StudentService.get_problem_set_detail(slug)

        serializer = ProblemSetSerializer(problem_set)
        data = serializer.data

        # Get ordered problems through service (includes test cases - optimized, no N+1)
        problems_data = StudentService.get_problem_set_problems(problem_set, user=request.user)

        # Test cases already included in problems_data from service (no additional queries needed)
        data['problems'] = problems_data
        return Response(data)


class CategoryListView(APIView):
    """List all problem categories."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Use service layer
        categories = StudentService.get_all_categories()
        serializer = ProblemCategorySerializer(categories, many=True)
        return Response(serializer.data)