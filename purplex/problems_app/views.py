import json
import logging
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.db.models import Count
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import transaction
from django.db.models import Prefetch
from django.conf import settings
from datetime import timedelta

from .models import Problem, ProblemSet, ProblemCategory, TestCase, ProblemSetMembership, UserProgress, UserProblemSetProgress
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
        # Optimized query - include all fields needed by ProblemSetListSerializer
        problem_sets = ProblemSet.objects.filter(is_public=True).prefetch_related(
            'problems'
        ).only(
            'slug', 'title', 'description', 'icon', 'is_public', 'created_at'
        )
        serializer = ProblemSetListSerializer(problem_sets, many=True)
        
        # Add full URLs for icons
        for problem_set, data in zip(problem_sets, serializer.data):
            if problem_set.icon:
                data['icon'] = SERVER_URL + problem_set.icon.url
                
        return Response(serializer.data)

class ProblemSetDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, slug):
        # Optimized query with select_related for foreign keys and prefetch for many-to-many
        problem_set = get_object_or_404(
            ProblemSet.objects.select_related('created_by').prefetch_related(
                Prefetch(
                    'problemsetmembership_set',
                    queryset=ProblemSetMembership.objects.select_related(
                        'problem'
                    ).prefetch_related(
                        'problem__categories',
                        'problem__test_cases'
                    ).order_by('order')
                )
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
        
        # Run tests with error handling
        try:
            code_service = CodeExecutionService()
            result = code_service.test_solution(user_code, problem.function_name, test_data)
            return Response(result)
        except Exception as e:
            logger.error(f"Code execution failed for problem {problem_slug}: {str(e)}")
            return Response({
                'error': 'Code execution failed. Please check your solution and try again.',
                'passed': 0,
                'total': len(test_data),
                'results': []
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SubmitSolutionView(APIView):
    """Submit a solution and track progress"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        problem_slug = request.data.get('problem_slug')
        problem_set_slug = request.data.get('problem_set_slug')
        user_code = request.data.get('user_code')
        prompt = request.data.get('prompt', '')  # For EiPL problems
        time_spent = request.data.get('time_spent')  # Optional, in seconds
        course_id = request.data.get('course_id')  # Optional, for course context
        
        if not problem_slug or not user_code or not problem_set_slug:
            return Response({
                'error': 'problem_slug, problem_set_slug, and user_code are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            problem = Problem.objects.get(slug=problem_slug, is_active=True)
            problem_set = ProblemSet.objects.get(slug=problem_set_slug)
        except Problem.DoesNotExist:
            return Response({
                'error': 'Problem not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except ProblemSet.DoesNotExist:
            return Response({
                'error': 'Problem set not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Verify problem belongs to the problem set
        if not problem.problem_sets.filter(id=problem_set.id).exists():
            return Response({
                'error': 'Problem does not belong to the specified problem set'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate course context if provided
        course = None
        if course_id:
            try:
                from .models import Course, CourseEnrollment
                course = Course.objects.get(course_id=course_id, is_active=True, is_deleted=False)
                
                # Verify user is enrolled in the course
                if not CourseEnrollment.objects.filter(
                    user=request.user,
                    course=course,
                    is_active=True
                ).exists():
                    return Response({
                        'error': 'You are not enrolled in this course'
                    }, status=status.HTTP_403_FORBIDDEN)
                
                # Verify problem set belongs to the course
                if not course.problem_sets.filter(id=problem_set.id).exists():
                    return Response({
                        'error': 'This problem set is not part of the specified course'
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
            except Course.DoesNotExist:
                return Response({
                    'error': 'Course not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        # Get ALL test cases for scoring (including hidden ones)
        all_test_cases = problem.test_cases.all()
        test_data = [
            {
                'id': tc.id,
                'inputs': tc.inputs,
                'expected_output': tc.expected_output,
                'description': tc.description
            }
            for tc in all_test_cases
        ]
        
        # Run tests with error handling
        try:
            code_service = CodeExecutionService()
            result = code_service.test_solution(user_code, problem.function_name, test_data)
            
            # Calculate score based on all tests
            passed_tests = result.get('passed', 0)
            total_tests = result.get('total', 0)
            score = int((passed_tests / total_tests * 100) if total_tests > 0 else 0)
        except Exception as e:
            logger.error(f"Code execution failed for problem {problem_slug}: {str(e)}")
            return Response({
                'error': 'Code execution failed. Please check your solution and try again.',
                'submission_id': None,
                'score': 0,
                'passed': 0,
                'total': len(test_data),
                'results': []
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Extract passed test IDs
        passed_test_ids = []
        if 'results' in result:
            for i, test_result in enumerate(result['results']):
                if test_result.get('passed', False) and i < len(test_data):
                    passed_test_ids.append(test_data[i]['id'])
        
        # Convert time_spent to timedelta if provided
        time_spent_delta = None
        if time_spent:
            time_spent_delta = timedelta(seconds=int(time_spent))
        
        # Create submission record
        from purplex.submissions_app.models import PromptSubmission
        submission = PromptSubmission.objects.create(
            user=request.user,
            problem=problem,
            problem_set=problem_set,
            score=score,
            prompt=prompt or user_code,  # Store code if no prompt provided
            feedback=json.dumps(result),
            passed_test_ids=passed_test_ids,
            time_spent=time_spent_delta
        )
        
        # Set course context for progress tracking
        if course:
            submission._course = course
        
        # Progress is automatically updated via the model's save method
        # Force save to trigger progress update with course context
        submission.save()
        
        # Get updated progress
        progress = UserProgress.objects.get(
            user=request.user, 
            problem=problem,
            problem_set=problem_set,
            course=course  # Include course in progress lookup
        )
        
        # Return only visible test results to student
        visible_results = []
        if 'results' in result:
            visible_test_cases = list(problem.test_cases.filter(is_hidden=False))
            for i, tc in enumerate(all_test_cases):
                if not tc.is_hidden and i < len(result['results']):
                    visible_results.append(result['results'][i])
        
        return Response({
            'submission_id': submission.id,
            'score': score,
            'passed': passed_tests,
            'total': total_tests,
            'results': visible_results,  # Only visible test results
            'progress': {
                'status': progress.status,
                'best_score': progress.best_score,
                'attempts': progress.attempts,
                'is_completed': progress.is_completed,
            }
        })


class EiPLSubmissionView(APIView):
    """Unified endpoint for EiPL (Explain in Plain Language) submissions.
    Generates AI variations, tests them, and saves submission with progress tracking."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        problem_slug = request.data.get('problem_slug')
        problem_set_slug = request.data.get('problem_set_slug')
        user_prompt = request.data.get('prompt', '')
        course_id = request.data.get('course_id')  # Optional, for course context
        
        if not problem_slug or not user_prompt or not problem_set_slug:
            return Response({
                'error': 'problem_slug, problem_set_slug, and prompt are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            problem = Problem.objects.get(slug=problem_slug, is_active=True)
            problem_set = ProblemSet.objects.get(slug=problem_set_slug)
        except Problem.DoesNotExist:
            return Response({
                'error': 'Problem not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except ProblemSet.DoesNotExist:
            return Response({
                'error': 'Problem set not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Verify problem belongs to the problem set
        if not problem.problem_sets.filter(id=problem_set.id).exists():
            return Response({
                'error': 'Problem does not belong to the specified problem set'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify this is an EiPL problem
        if problem.problem_type != 'eipl':
            return Response({
                'error': 'This endpoint is only for EiPL problems'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate AI variations using problem-specific prompt with error handling
        try:
            ai_service = AITestGenerationService()
            generation_result = ai_service.generate_eipl_variations(
                problem=problem,
                user_prompt=user_prompt
            )
            
            if not generation_result['success']:
                return Response({
                    'error': generation_result.get('error', 'Failed to generate code variations')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"AI service failed for problem {problem_slug}: {str(e)}")
            return Response({
                'error': 'AI service temporarily unavailable. Please try again later.'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        code_variations = generation_result['variations']
        
        # Get all test cases (including hidden ones for scoring)
        all_test_cases = list(problem.test_cases.all().order_by('order'))
        test_data = [
            {
                'inputs': tc.inputs,
                'expected_output': tc.expected_output,
                'description': tc.description,
                'is_hidden': tc.is_hidden
            }
            for tc in all_test_cases
        ]
        
        # Test all variations with error handling
        try:
            code_service = CodeExecutionService()
        except Exception as e:
            logger.error(f"Failed to initialize code service: {str(e)}")
            return Response({
                'error': 'Code execution service unavailable. Please try again later.'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
        all_results = []
        total_passed = 0
        failed_variations = 0
        
        for i, variation in enumerate(code_variations):
            try:
                result = code_service.test_solution(variation, problem.function_name, test_data)
            except Exception as e:
                logger.warning(f"Code execution failed for variation {i} in problem {problem_slug}: {str(e)}")
                # Create a failed result for this variation
                result = {
                    'success': False,
                    'passed': 0,
                    'total': len(test_data),
                    'results': [{'passed': False, 'error': 'Execution failed'} for _ in test_data]
                }
                failed_variations += 1
            
            # Format results for frontend (convert 'passed' to 'pass' and add function_call)
            formatted_results = []
            for i, test_result in enumerate(result.get('results', [])):
                # Generate function call string
                inputs = test_result.get('inputs', [])
                function_call = f"{problem.function_name}({', '.join(repr(inp) for inp in inputs)})"
                
                formatted_result = {
                    'pass': test_result.get('passed', False),
                    'function_call': function_call,
                    'expected_output': test_result.get('expected_output'),
                    'actual_output': test_result.get('actual_output'),
                    'error': test_result.get('error'),
                    'description': test_result.get('description'),
                    'is_hidden': test_data[i]['is_hidden'] if i < len(test_data) else False
                }
                
                # Only include visible tests in response
                if not formatted_result['is_hidden']:
                    formatted_results.append(formatted_result)
                    
            all_results.append(formatted_results)
            
            # Count variations where all tests pass
            if result.get('success') and result.get('passed') == result.get('total'):
                total_passed += 1
        
        # Calculate score based on how many variations passed all tests
        if not code_variations:
            logger.warning(f"No code variations generated for problem {problem_slug}")
            return Response({
                'error': 'No code variations could be generated. Please try rephrasing your explanation.'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        score = (total_passed / len(code_variations) * 100)
        
        # Log if many variations failed
        if failed_variations > len(code_variations) / 2:
            logger.warning(f"High failure rate in problem {problem_slug}: {failed_variations}/{len(code_variations)} variations failed")
        
        # Create submission record
        from purplex.submissions_app.models import PromptSubmission
        submission = PromptSubmission.objects.create(
            user=request.user,
            problem=problem,
            problem_set=problem_set,
            prompt=user_prompt,
            user_solution=json.dumps({
                'prompt': user_prompt,
                'variations': code_variations,
                'results': all_results
            }),
            score=score,
            feedback=json.dumps({
                'total_variations': len(code_variations),
                'passing_variations': total_passed,
                'test_results': all_results
            }),
            submitted_by=request.user.email,
            firebase_uid=getattr(request.user, 'firebase_uid', '')
        )
        
        # Update user progress - now includes problem_set context
        progress, created = UserProgress.objects.get_or_create(
            user=request.user,
            problem=problem,
            problem_set=problem_set
        )

        # Update progress with the submission score
        try:
            progress.update_progress(score, timedelta(seconds=0))
            logger.info(f"Updated progress for user {request.user.id}, problem {problem.slug}, score {score}")
        except Exception as e:
            logger.error(f"Failed to update progress for user {request.user.id}, problem {problem.slug}: {str(e)}")
            # Continue execution even if progress update fails

        
        return Response({
            'submission_id': submission.id,
            'score': score,
            'code_variations': code_variations,
            'test_results': all_results,
            'passing_variations': total_passed,
            'total_variations': len(code_variations),
            'progress': {
                'status': progress.status,
                'best_score': progress.best_score,
                'attempts': progress.attempts,
                'is_completed': progress.is_completed,
            }
        })


# Admin Views
class AdminProblemListView(APIView):
    permission_classes = [IsAdmin]
    
    def get(self, request):
        # Fixed N+1 query: add select_related for created_by since AdminProblemSerializer uses it
        problems = Problem.objects.all().select_related('created_by').prefetch_related('categories', 'test_cases', 'problem_sets')
        serializer = AdminProblemSerializer(problems, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        data = request.data.copy()
        
        # Handle category transformation (string to category_ids array) with transaction safety
        if 'category' in data and data['category']:
            # Try to find or create the category
            category_name = data.pop('category')
            try:
                category = ProblemCategory.objects.get(name__iexact=category_name)
                data['category_ids'] = [category.id]
            except ProblemCategory.DoesNotExist:
                # Create a new category if it doesn't exist
                with transaction.atomic():
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
            try:
                with transaction.atomic():
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
                                logger.warning(f"Problem set with slug '{slug}' not found during problem creation")
                    
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
            try:
                with transaction.atomic():
                    problem = serializer.save()
                    
                    # Handle problem sets relationship if provided
                    if problem_sets_slugs is not None:
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
                'passed': 0,
                'total': len(problem_data.get('test_cases', [])),
                'results': []
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
            category = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Progress Tracking Views
class UserProgressView(APIView):
    """Get user's progress for a specific problem or all problems"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, problem_slug=None):
        user = request.user
        
        if problem_slug:
            # Get progress for specific problem
            problem = get_object_or_404(Problem, slug=problem_slug)
            try:
                progress = UserProgress.objects.get(user=user, problem=problem)
                return Response({
                    'problem_slug': problem.slug,
                    'status': progress.status,
                    'best_score': progress.best_score,
                    'attempts': progress.attempts,
                    'is_completed': progress.is_completed,
                    'completion_percentage': progress.completion_percentage,
                    'last_attempt': progress.last_attempt,
                    'completed_at': progress.completed_at,
                })
            except UserProgress.DoesNotExist:
                return Response({
                    'problem_slug': problem.slug,
                    'status': 'not_started',
                    'best_score': 0,
                    'attempts': 0,
                    'is_completed': False,
                    'completion_percentage': 0,
                    'last_attempt': None,
                    'completed_at': None,
                })
        else:
            # Get all progress for user
            progress_list = UserProgress.objects.filter(user=user).select_related('problem')
            progress_data = []
            
            for progress in progress_list:
                progress_data.append({
                    'problem_slug': progress.problem.slug,
                    'problem_title': progress.problem.title,
                    'status': progress.status,
                    'best_score': progress.best_score,
                    'attempts': progress.attempts,
                    'is_completed': progress.is_completed,
                    'completion_percentage': progress.completion_percentage,
                    'last_attempt': progress.last_attempt,
                })
            
            return Response(progress_data)


class ProblemSetProgressView(APIView):
    """Get user's progress for a problem set"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, slug):
        user = request.user
        problem_set = get_object_or_404(ProblemSet, slug=slug)
        
        # Get or create problem set progress
        set_progress, created = UserProblemSetProgress.objects.get_or_create(
            user=user,
            problem_set=problem_set,
            defaults={'total_problems': problem_set.problems.count()}
        )
        
        # If created, update the progress
        if created:
            # For new problem set progress, we'll update it based on any existing progress
            first_progress = UserProgress.objects.filter(
                user=user,
                problem_set=problem_set
            ).first()
            if first_progress:
                UserProblemSetProgress.update_from_progress(first_progress)
                set_progress.refresh_from_db()
        
        # Get individual problem progress - Fixed N+1 query
        # Prefetch progress data to avoid querying UserProgress for each problem
        memberships = problem_set.problemsetmembership_set.all().select_related('problem').prefetch_related(
            'problem__userprogress_set'
        )
        
        # Get all progress for this user and problem set in one query
        user_progress_dict = {}
        user_progresses = UserProgress.objects.filter(
            user=user,
            problem_set=problem_set
        ).select_related('problem')
        
        for progress in user_progresses:
            user_progress_dict[progress.problem.id] = progress
        
        problems_progress = []
        for membership in memberships:
            problem = membership.problem
            progress = user_progress_dict.get(problem.id)
            
            if progress:
                status = progress.status
                best_score = progress.best_score
                attempts = progress.attempts
            else:
                status = 'not_started'
                best_score = 0
                attempts = 0
            
            problems_progress.append({
                'problem_slug': problem.slug,
                'problem_title': problem.title,
                'order': membership.order,
                'status': status,
                'best_score': best_score,
                'attempts': attempts,
            })
        
        # Sort by order
        problems_progress.sort(key=lambda x: x['order'])
        
        return Response({
            'problem_set': {
                'slug': problem_set.slug,
                'title': problem_set.title,
                'total_problems': set_progress.total_problems,
                'completed_problems': set_progress.completed_problems,
                'partially_complete_problems': set_progress.partially_complete_problems,
                'completion_percentage': set_progress.completion_percentage,
                'is_completed': set_progress.is_completed,
                'average_score': set_progress.average_score,
                'last_activity': set_progress.last_activity,
            },
            'problems_progress': problems_progress
        })


class UserProgressSummaryView(APIView):
    """Get summary of user's progress across all problem sets"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            user = request.user
            
            # Get all public problem sets first - this is safer
            all_problem_sets = ProblemSet.objects.filter(is_public=True)
            
            # Try to get existing progress records
            try:
                set_progresses = UserProblemSetProgress.objects.filter(
                    user=user,
                    problem_set__is_public=True
                ).select_related('problem_set')
                tracked_set_ids = [p.problem_set_id for p in set_progresses]
            except Exception as progress_error:
                # If there's an error with progress tracking, just return basic data
                logger.warning(f"Progress tracking error: {str(progress_error)}, falling back to basic data")
                set_progresses = []
                tracked_set_ids = []
            
            summary_data = []
            
            # Add tracked problem sets with progress
            for progress in set_progresses:
                summary_data.append({
                    'problem_set_slug': progress.problem_set.slug,
                    'problem_set_title': progress.problem_set.title,
                    'total_problems': progress.total_problems,
                    'completed_problems': progress.completed_problems,
                    'partially_complete_problems': progress.partially_complete_problems,
                    'completion_percentage': progress.completion_percentage,
                    'is_completed': progress.is_completed,
                    'last_activity': progress.last_activity,
                })
            
            # Add problem sets with no progress (or if progress tracking failed)
            # Fixed N+1 query: use annotate to get problem count in a single query
            untracked_sets = all_problem_sets.exclude(id__in=tracked_set_ids).annotate(
                problems_count=Count('problems')
            )
            
            for problem_set in untracked_sets:
                summary_data.append({
                    'problem_set_slug': problem_set.slug,
                    'problem_set_title': problem_set.title,
                    'total_problems': problem_set.problems_count,
                    'completed_problems': 0,
                    'partially_complete_problems': 0,
                    'completion_percentage': 0,
                    'is_completed': False,
                    'last_activity': None,
                })
            
            # Calculate overall stats
            total_problems = sum(s['total_problems'] for s in summary_data)
            total_completed = sum(s['completed_problems'] for s in summary_data)
            total_partially_complete = sum(s['partially_complete_problems'] for s in summary_data)
            
            return Response({
                'overall': {
                    'total_problems': total_problems,
                    'completed_problems': total_completed,
                    'partially_complete_problems': total_partially_complete,
                    'completion_percentage': int((total_completed / total_problems * 100) if total_problems > 0 else 0),
                },
                'problem_sets': summary_data
            })
            
        except Exception as e:
            logger.error(f"Error in UserProgressSummaryView: {str(e)}")
            # Return a minimal response so the frontend doesn't break
            return Response({
                'overall': {
                    'total_problems': 0,
                    'completed_problems': 0,
                    'partially_complete_problems': 0,
                    'completion_percentage': 0,
                },
                'problem_sets': []
            })
