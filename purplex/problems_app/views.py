import json
import logging
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import transaction
from django.conf import settings

from .models import Problem, ProblemSet, ProblemCategory, TestCase, ProblemSetMembership
from .serializers import (
    ProblemSerializer, ProblemSetSerializer, ProblemCategorySerializer,
    TestCaseSerializer, AdminProblemSerializer, ProblemListSerializer,
    ProblemSetListSerializer
)
from .services import CodeExecutionService, AITestGenerationService, ProblemValidationService
from purplex.users_app.permissions import IsAdmin, IsAdminOrReadOnly, IsAuthenticated

logger = logging.getLogger(__name__)
SERVER_URL = getattr(settings, 'SERVER_URL', 'http://localhost:8000')

# Public/Student Views
class ProblemListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        problems = Problem.objects.filter(is_active=True).prefetch_related('categories', 'test_cases', 'problem_sets')
        serializer = ProblemListSerializer(problems, many=True)
        return Response(serializer.data)

class ProblemDetailView(APIView):
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
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        problem_sets = ProblemSet.objects.filter(is_public=True).prefetch_related('problems')
        serializer = ProblemSetListSerializer(problem_sets, many=True)
        
        # Add full URLs for icons
        for problem_set, data in zip(problem_sets, serializer.data):
            if problem_set.icon:
                data['icon'] = SERVER_URL + problem_set.icon.url
                
        return Response(serializer.data)

class ProblemSetDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, slug):
        problem_set = get_object_or_404(
            ProblemSet.objects.prefetch_related(
                'problemsetmembership_set__problem__categories',
                'problemsetmembership_set__problem__test_cases'
            ),
            slug=slug, 
            is_public=True
        )
        serializer = ProblemSetSerializer(problem_set)
        data = serializer.data
        
        if problem_set.icon:
            data['icon'] = SERVER_URL + problem_set.icon.url
        
        # Extract problems from problems_detail for easier frontend access
        if 'problems_detail' in data:
            data['problems'] = [item['problem'] for item in data['problems_detail']]
            
        return Response(data)

class CategoryListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        categories = ProblemCategory.objects.all()
        serializer = ProblemCategorySerializer(categories, many=True)
        return Response(serializer.data)

# Testing and Validation Views
class TestSolutionView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        problem_slug = request.data.get('problem_slug')
        user_code = request.data.get('user_code')
        
        if not problem_slug or not user_code:
            return Response({
                'error': 'problem_slug and user_code are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            problem = Problem.objects.get(slug=problem_slug, is_active=True)
        except Problem.DoesNotExist:
            return Response({
                'error': 'Problem not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get test cases (only visible ones for students)
        test_cases = problem.test_cases.filter(is_hidden=False)
        test_data = [
            {
                'inputs': tc.inputs,
                'expected_output': tc.expected_output,
                'description': tc.description
            }
            for tc in test_cases
        ]
        
        # Run tests
        code_service = CodeExecutionService()
        result = code_service.test_solution(user_code, problem.function_name, test_data)
        
        return Response(result)

# Admin Views
class AdminProblemListView(APIView):
    permission_classes = [IsAdmin]
    
    def get(self, request):
        problems = Problem.objects.all().prefetch_related('categories', 'test_cases', 'problem_sets')
        serializer = AdminProblemSerializer(problems, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        data = request.data.copy()
        
        # Handle category transformation (string to category_ids array)
        if 'category' in data and data['category']:
            # Try to find or create the category
            category_name = data.pop('category')
            try:
                category = ProblemCategory.objects.get(name__iexact=category_name)
                data['category_ids'] = [category.id]
            except ProblemCategory.DoesNotExist:
                # Create a new category if it doesn't exist
                category = ProblemCategory.objects.create(
                    name=category_name,
                    description=f"Category for {category_name} problems"
                )
                data['category_ids'] = [category.id]
        
        # Handle problem_sets transformation
        problem_set_slugs = data.pop('problem_sets', [])
        
        # Set default values for EiPL problems
        if data.get('problem_type') == 'eipl':
            # For EiPL, we need to provide default values for required function fields
            if not data.get('function_name'):
                data['function_name'] = 'explain_code'
            if not data.get('function_signature'):
                data['function_signature'] = 'def explain_code():'
        
        serializer = AdminProblemSerializer(data=data)
        if serializer.is_valid():
            problem = serializer.save(created_by=request.user)
            
            # Handle problem set assignments after problem is created
            if problem_set_slugs:
                for slug in problem_set_slugs:
                    try:
                        problem_set = ProblemSet.objects.get(slug=slug)
                        ProblemSetMembership.objects.create(
                            problem_set=problem_set,
                            problem=problem,
                            order=problem_set.problems.count()
                        )
                    except ProblemSet.DoesNotExist:
                        pass
            
            # Return the serialized problem with all relations
            serializer = AdminProblemSerializer(problem)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdminProblemDetailView(APIView):
    permission_classes = [IsAdmin]
    
    def get(self, request, slug):
        problem = get_object_or_404(Problem, slug=slug)
        serializer = AdminProblemSerializer(problem)
        return Response(serializer.data)
    
    def put(self, request, slug):
        problem = get_object_or_404(Problem, slug=slug)
        
        # Create a mutable copy of request data
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        
        # Handle category transformation
        if 'category' in data and data['category']:
            category_name = data['category']
            category, created = ProblemCategory.objects.get_or_create(
                name=category_name,
                defaults={'description': f'{category_name} category'}
            )
            data['category_ids'] = [category.id]
            del data['category']
        
        # Extract problem_sets for later processing
        problem_sets_slugs = data.pop('problem_sets', None)
        
        # Handle EiPL problems - provide defaults for required fields
        if data.get('problem_type') == 'eipl':
            if not data.get('function_name'):
                data['function_name'] = 'explain_code'
            if not data.get('function_signature'):
                data['function_signature'] = 'def explain_code():'
        
        serializer = AdminProblemSerializer(problem, data=data, partial=True)
        if serializer.is_valid():
            problem = serializer.save()
            problem.version += 1
            problem.save()
            
            # Handle problem sets relationship if provided
            if problem_sets_slugs is not None:
                problem_sets = ProblemSet.objects.filter(slug__in=problem_sets_slugs)
                problem.problem_sets.set(problem_sets)
            
            # Return fresh data with all relationships
            return Response(AdminProblemSerializer(problem).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, slug):
        problem = get_object_or_404(Problem, slug=slug)
        problem.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class AdminTestProblemView(APIView):
    permission_classes = [IsAdmin]
    
    def post(self, request):
        """Test a problem's reference solution against its test cases"""
        problem_data = request.data
        
        # Validate the problem
        validation_service = ProblemValidationService()
        is_valid, errors = validation_service.validate_problem(problem_data)
        
        if not is_valid:
            return Response({
                'success': False,
                'errors': errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Test the reference solution
        code_service = CodeExecutionService()
        result = code_service.test_solution(
            problem_data['reference_solution'],
            problem_data['function_name'],
            problem_data.get('test_cases', [])
        )
        
        return Response(result)

class AdminGenerateTestCasesView(APIView):
    permission_classes = [IsAdmin]
    
    def post(self, request):
        """Generate test cases using AI"""
        ai_service = AITestGenerationService()
        
        problem_description = request.data.get('description', '')
        function_name = request.data.get('function_name', '')
        function_signature = request.data.get('function_signature', '')
        reference_solution = request.data.get('reference_solution', '')
        
        test_cases = ai_service.generate_test_cases(
            problem_description, function_name, function_signature, reference_solution
        )
        
        return Response({
            'test_cases': test_cases
        })

class AdminTestCaseView(APIView):
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
    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get(self, request):
        problem_sets = ProblemSet.objects.all().prefetch_related('problems')
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
        
        # Check for duplicate title/slug
        title = request.data.get('title', '')
        potential_slug = slugify(title)
        if ProblemSet.objects.filter(slug=potential_slug).exists():
            return Response({
                'title': [f'A problem set with similar title already exists (slug: {potential_slug})']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = ProblemSetSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    problem_set = serializer.save(created_by=request.user)
                    
                    # Handle problems assignment
                    problem_slugs = request.data.get('problem_slugs', [])
                    if problem_slugs:
                        # Parse JSON string if needed
                        if isinstance(problem_slugs, str):
                            try:
                                problem_slugs = json.loads(problem_slugs)
                            except json.JSONDecodeError:
                                raise ValidationError('Invalid problem_slugs format - must be a JSON array')
                        
                        # Validate that problem_slugs is a list
                        if not isinstance(problem_slugs, list):
                            raise ValidationError('problem_slugs must be an array')
                        
                        # Collect missing problems for better error reporting
                        missing_problems = []
                        added_problems = []
                        
                        for order, slug in enumerate(problem_slugs):
                            try:
                                problem = Problem.objects.get(slug=slug)
                                ProblemSetMembership.objects.create(
                                    problem_set=problem_set,
                                    problem=problem,
                                    order=order
                                )
                                added_problems.append(slug)
                            except Problem.DoesNotExist:
                                missing_problems.append(slug)
                        
                        # Report if some problems were not found
                        if missing_problems:
                            # Still return success but with a warning
                            logger.warning(f"Problem set created but some problems not found: {missing_problems}")
                    
                    response_data = serializer.data
                    if problem_set.icon:
                        response_data['icon'] = SERVER_URL + problem_set.icon.url
                    
                    # Add info about problems added
                    if problem_slugs:
                        response_data['problems_added'] = len(added_problems)
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
        
        # Check if title is being changed and would create a duplicate
        if 'title' in request.data:
            new_title = request.data['title']
            potential_slug = slugify(new_title)
            # Check if another problem set already has this slug
            if potential_slug != slug and ProblemSet.objects.filter(slug=potential_slug).exists():
                return Response({
                    'title': [f'A problem set with similar title already exists (slug: {potential_slug})']
                }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = ProblemSetSerializer(problem_set, data=request.data, partial=True)
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    problem_set = serializer.save()
                    
                    # Handle problems update
                    problem_slugs = request.data.get('problem_slugs')
                    if problem_slugs is not None:
                        # Parse JSON string if needed
                        if isinstance(problem_slugs, str):
                            try:
                                problem_slugs = json.loads(problem_slugs)
                            except json.JSONDecodeError:
                                raise ValidationError('Invalid problem_slugs format - must be a JSON array')
                        
                        # Validate that problem_slugs is a list
                        if not isinstance(problem_slugs, list):
                            raise ValidationError('problem_slugs must be an array')
                        
                        # Clear existing memberships
                        ProblemSetMembership.objects.filter(problem_set=problem_set).delete()
                        
                        # Collect missing problems for better error reporting
                        missing_problems = []
                        added_problems = []
                        
                        # Add new memberships
                        for order, slug in enumerate(problem_slugs):
                            try:
                                problem = Problem.objects.get(slug=slug)
                                ProblemSetMembership.objects.create(
                                    problem_set=problem_set,
                                    problem=problem,
                                    order=order
                                )
                                added_problems.append(slug)
                            except Problem.DoesNotExist:
                                missing_problems.append(slug)
                        
                        # Report if some problems were not found
                        if missing_problems:
                            logger.warning(f"Problem set updated but some problems not found: {missing_problems}")
                    
                    response_data = serializer.data
                    if problem_set.icon:
                        response_data['icon'] = SERVER_URL + problem_set.icon.url
                    
                    # Add info about problems update
                    if problem_slugs is not None:
                        response_data['problems_updated'] = len(added_problems)
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
    permission_classes = [IsAdmin]
    
    def get(self, request):
        categories = ProblemCategory.objects.all()
        serializer = ProblemCategorySerializer(categories, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = ProblemCategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        category = get_object_or_404(ProblemCategory, pk=pk)
        serializer = ProblemCategorySerializer(category, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        category = get_object_or_404(ProblemCategory, pk=pk)
        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)