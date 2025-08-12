"""Admin views for managing problems, test cases, and problem sets."""

import json
import logging
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.db import transaction
from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from ..models import Problem, ProblemSet, ProblemCategory, TestCase, ProblemSetMembership
from ..serializers import (
    AdminProblemSerializer, ProblemSetSerializer, ProblemCategorySerializer,
    TestCaseSerializer
)
from ..services.code_execution_service import CodeExecutionService
from ..services.admin_service import AdminProblemService
from purplex.users_app.permissions import IsAdmin

logger = logging.getLogger(__name__)
SERVER_URL = getattr(settings, 'SERVER_URL', 'http://localhost:8000')


class AdminProblemListView(APIView):
    """Admin view for listing and creating problems."""
    permission_classes = [IsAdmin]
    
    def get(self, request):
        # Fixed N+1 query: add select_related for created_by since AdminProblemSerializer uses it
        problems = Problem.objects.all().select_related('created_by').prefetch_related('categories', 'test_cases', 'problem_sets')
        serializer = AdminProblemSerializer(problems, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        # Use service layer to prepare data
        data, problem_set_slugs = AdminProblemService.prepare_problem_data(request.data)
        
        serializer = AdminProblemSerializer(data=data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    problem = serializer.save(created_by=request.user)
                    
                    # Use service layer to handle problem set assignments
                    if problem_set_slugs:
                        AdminProblemService.create_problem_with_relations(
                            problem, problem_set_slugs
                        )
                    
                    # Return the serialized problem with all relations
                    serializer = AdminProblemSerializer(problem)
                    return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                logger.error(f"Failed to create problem: {str(e)}")
                return Response({
                    'error': 'Failed to create problem. Please try again.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminProblemDetailView(APIView):
    """Admin view for getting, updating, and deleting specific problems."""
    permission_classes = [IsAdmin]
    
    def get(self, request, slug):
        problem = get_object_or_404(Problem, slug=slug)
        serializer = AdminProblemSerializer(problem)
        return Response(serializer.data)
    
    def put(self, request, slug):
        problem = get_object_or_404(Problem, slug=slug)
        
        # Use service layer to prepare data
        data, problem_sets_slugs = AdminProblemService.prepare_problem_data(request.data)
        
        serializer = AdminProblemSerializer(problem, data=data, partial=True)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    problem = serializer.save()
                    
                    # Use service layer to handle problem sets relationship
                    # Only update problem sets if explicitly provided in the request
                    if 'problem_sets' in request.data:
                        problem_sets = ProblemSet.objects.filter(slug__in=problem_sets_slugs)
                        problem.problem_sets.set(problem_sets)
                    
                    # Return fresh data with all relationships
                    return Response(AdminProblemSerializer(problem).data)
            except Exception as e:
                logger.error(f"Failed to update problem {slug}: {str(e)}")
                logger.error(f"Exception type: {type(e).__name__}")
                logger.error(f"Exception args: {e.args}")
                
                # Import traceback for more detailed error information
                import traceback
                logger.error(f"Full traceback: {traceback.format_exc()}")
                
                return Response({
                    'error': f'Failed to update problem: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, slug):
        problem = get_object_or_404(Problem, slug=slug)
        problem.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminTestProblemView(APIView):
    """Admin view for testing problem reference solutions."""
    permission_classes = [IsAdmin]
    
    def post(self, request):
        """Test a problem's reference solution against its test cases"""
        problem_data = request.data
        
        # Basic validation
        required_fields = ['function_name', 'reference_solution', 'test_cases']
        for field in required_fields:
            if not problem_data.get(field):
                return Response({
                    'success': False,
                    'error': f'{field} is required for testing',
                }, status=status.HTTP_400_BAD_REQUEST)
        
        if not problem_data.get('test_cases') or len(problem_data['test_cases']) == 0:
            return Response({
                'success': False,
                'error': 'At least one test case is required for testing',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Test the reference solution with error handling
        try:
            code_service = CodeExecutionService()
            result = code_service.test_solution(
                problem_data['reference_solution'],
                problem_data['function_name'],
                problem_data.get('test_cases', [])
            )
            return Response(result)
        except Exception as e:
            logger.error(f"Reference solution testing failed: {str(e)}")
            return Response({
                'success': False,
                'error': 'Failed to test reference solution. Please check the code and try again.',
                'testsPassed': 0,
                'totalTests': len(problem_data.get('test_cases', [])),
                'results': []
            })


class AdminTestCaseView(APIView):
    """Admin view for managing test cases."""
    permission_classes = [IsAdmin]
    
    def post(self, request, problem_slug):
        """Add test case to a problem"""
        problem = get_object_or_404(Problem, slug=problem_slug)
        
        serializer = TestCaseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(problem=problem)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, problem_slug, test_case_id):
        """Update a test case"""
        test_case = get_object_or_404(TestCase, id=test_case_id, problem__slug=problem_slug)
        
        serializer = TestCaseSerializer(test_case, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, problem_slug, test_case_id):
        """Delete a test case"""
        test_case = get_object_or_404(TestCase, id=test_case_id, problem__slug=problem_slug)
        test_case.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminProblemSetListView(APIView):
    """Admin view for listing and creating problem sets."""
    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get(self, request):
        problem_sets = ProblemSet.objects.all().select_related('created_by').prefetch_related('problems')
        serializer = ProblemSetSerializer(problem_sets, many=True)
        
        # Add full URLs for icons
        for problem_set, data in zip(problem_sets, serializer.data):
            if problem_set.icon:
                data['icon'] = SERVER_URL + problem_set.icon.url
                
        return Response(serializer.data)
    
    def post(self, request):
        """Create a new problem set"""
        # Validate required fields
        if not request.data.get('title'):
            return Response({'title': ['This field is required.']}, status=status.HTTP_400_BAD_REQUEST)
        
        # Use service to check for duplicate title/slug
        title = request.data.get('title', '')
        error_msg = AdminProblemService.validate_problem_set_title(title)
        if error_msg:
            return Response({'title': [error_msg]}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = ProblemSetSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    problem_set = serializer.save(created_by=request.user)
                    
                    # Use service to handle problems assignment
                    problem_slugs = request.data.get('problem_slugs', [])
                    if problem_slugs:
                        result = AdminProblemService.create_problem_set_with_problems(
                            problem_set, problem_slugs
                        )
                        added_problems = result['problems_added']
                        missing_problems = result['missing_problems']
                    
                    response_data = serializer.data
                    if problem_set.icon:
                        response_data['icon'] = SERVER_URL + problem_set.icon.url
                    
                    # Add info about problems added
                    if problem_slugs:
                        response_data['problems_added'] = added_problems
                        if missing_problems:
                            response_data['warnings'] = [f"Problems not found: {', '.join(missing_problems)}"]
                    
                    return Response(response_data, status=status.HTTP_201_CREATED)
                    
            except ValidationError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(f"Error creating problem set: {str(e)}")
                return Response({
                    'error': 'An error occurred while creating the problem set. Please try again.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminProblemSetDetailView(APIView):
    """Admin view for getting, updating, and deleting specific problem sets."""
    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get(self, request, slug):
        problem_set = get_object_or_404(ProblemSet, slug=slug)
        serializer = ProblemSetSerializer(problem_set)
        data = serializer.data
        
        if problem_set.icon:
            data['icon'] = SERVER_URL + problem_set.icon.url
            
        return Response(data)
    
    def put(self, request, slug):
        problem_set = get_object_or_404(ProblemSet, slug=slug)
        
        # Use service to check if title change would create a duplicate
        if 'title' in request.data:
            error_msg = AdminProblemService.validate_problem_set_title(
                request.data['title'], current_slug=slug
            )
            if error_msg:
                return Response({'title': [error_msg]}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = ProblemSetSerializer(problem_set, data=request.data, partial=True)
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    problem_set = serializer.save()
                    
                    # Use service to handle problems update
                    problem_slugs = request.data.get('problem_slugs')
                    if problem_slugs is not None:
                        result = AdminProblemService.update_problem_set_with_problems(
                            problem_set, problem_slugs
                        )
                        added_problems = result.get('problems_updated', 0)
                        missing_problems = result.get('missing_problems', [])
                    
                    response_data = serializer.data
                    if problem_set.icon:
                        response_data['icon'] = SERVER_URL + problem_set.icon.url
                    
                    # Add info about problems update
                    if problem_slugs is not None:
                        response_data['problems_updated'] = added_problems
                        if missing_problems:
                            response_data['warnings'] = [f"Problems not found: {', '.join(missing_problems)}"]
                    
                    return Response(response_data)
                    
            except ValidationError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(f"Error updating problem set: {str(e)}")
                return Response({
                    'error': 'An error occurred while updating the problem set. Please try again.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, slug):
        problem_set = get_object_or_404(ProblemSet, slug=slug)
        problem_set.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminCategoryView(APIView):
    """Admin view for managing problem categories."""
    permission_classes = [IsAdmin]
    
    def get(self, request):
        categories = ProblemCategory.objects.all()
        serializer = ProblemCategorySerializer(categories, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = ProblemCategorySerializer(data=request.data)
        if serializer.is_valid():
            category = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


