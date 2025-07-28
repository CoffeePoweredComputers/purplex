"""Views for handling code submissions and testing."""

import json
import logging
from datetime import timedelta
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from ..models import Problem, ProblemSet, Course, CourseEnrollment, UserProgress
from ..services import CodeExecutionService, AITestGenerationService
from purplex.users_app.permissions import IsAuthenticated

logger = logging.getLogger(__name__)


class TestSolutionView(APIView):
    """Test a solution without saving submission."""
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
    """Submit a solution and track progress."""
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
                        'error': 'Problem set does not belong to this course'
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
            except Course.DoesNotExist:
                return Response({
                    'error': 'Course not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        # Get all test cases (including hidden ones for grading)
        all_test_cases = list(problem.test_cases.all())
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
                if test_result.get('pass', False) and i < len(test_data):
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
            test_results=result,
            course=course,  # Include course context
            time_spent=time_spent_delta
        )
        
        # Progress is automatically updated via the PromptSubmission model's save method
        # Get the updated progress for response
        progress = UserProgress.objects.get(
            user=request.user,
            problem=problem,
            problem_set=problem_set,
            course=course
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
        user_prompt = request.data.get('user_prompt', '')
        course_id = request.data.get('course_id')  # Optional, for course context
        
        if not problem_slug or not user_prompt:
            return Response({
                'error': 'problem_slug and user_prompt are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            problem = Problem.objects.get(slug=problem_slug, is_active=True)
        except Problem.DoesNotExist:
            return Response({
                'error': 'Problem not found'
            }, status=status.HTTP_404_NOT_FOUND)
            
        # Handle optional problem set
        problem_set = None
        if problem_set_slug:
            try:
                problem_set = ProblemSet.objects.get(slug=problem_set_slug)
                # Verify problem belongs to the problem set
                if not problem.problem_sets.filter(id=problem_set.id).exists():
                    return Response({
                        'error': 'Problem does not belong to the specified problem set'
                    }, status=status.HTTP_400_BAD_REQUEST)
            except ProblemSet.DoesNotExist:
                return Response({
                    'error': 'Problem set not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        # Validate course context if provided
        course = None
        if course_id:
            try:
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
                    
            except Course.DoesNotExist:
                return Response({
                    'error': 'Course not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        # Generate AI variations using problem-specific prompt with error handling
        try:
            ai_service = AITestGenerationService()
            generation_result = ai_service.generate_eipl_variations(
                problem=problem,
                user_prompt=user_prompt
            )
            
            if not generation_result.get('success', False):
                return Response({
                    'error': generation_result.get('error', 'Failed to generate code variations'),
                    'submission_id': None,
                    'score': 0,
                    'variations': [],
                    'results': [],
                    'passing_variations': 0,
                    'total_variations': 0
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
            code_variations = generation_result.get('variations', [])
            
        except Exception as e:
            logger.error(f"AI code generation failed for problem {problem_slug}: {str(e)}")
            return Response({
                'error': 'AI code generation failed. Please try again.',
                'submission_id': None,
                'score': 0,
                'variations': [],
                'results': [],
                'passing_variations': 0,
                'total_variations': 0
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Get all test cases (including hidden ones for full evaluation)
        all_test_cases = list(problem.test_cases.all())
        test_data = [
            {
                'id': tc.id,
                'inputs': tc.inputs,
                'expected_output': tc.expected_output,
                'description': tc.description
            }
            for tc in all_test_cases
        ]
        
        # Test all variations with error handling
        try:
            code_service = CodeExecutionService()
        except Exception as e:
            logger.error(f"Failed to initialize code service: {str(e)}")
            return Response({
                'error': 'Code testing service unavailable',
                'submission_id': None,
                'score': 0,
                'variations': code_variations,
                'results': [],
                'passing_variations': 0,
                'total_variations': len(code_variations)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        all_results = []
        total_passed = 0
        
        for i, code_variation in enumerate(code_variations):
            try:
                result = code_service.test_solution(code_variation, problem.function_name, test_data)
                all_results.append(result)
                
                # Count passing variations (100% pass rate)
                if result.get('passed', 0) == result.get('total', 0) and result.get('total', 0) > 0:
                    total_passed += 1
                    
            except Exception as e:
                logger.error(f"Testing variation {i} failed: {str(e)}")
                # Add failed result for this variation
                all_results.append({
                    'success': False,
                    'error': f'Testing failed: {str(e)}',
                    'passed': 0,
                    'total': len(test_data),
                    'results': []
                })
        
        # Calculate overall score based on percentage of variations that pass all tests
        if len(code_variations) > 0:
            score = int((total_passed / len(code_variations)) * 100)
        else:
            score = 0
        
        # Create submission record with all EiPL-specific data
        from purplex.submissions_app.models import PromptSubmission
        submission = PromptSubmission.objects.create(
            user=request.user,
            problem=problem,
            problem_set=problem_set,
            score=score,
            prompt=user_prompt,
            code_variations=code_variations,
            test_results=all_results,
            passing_variations=total_passed,
            total_variations=len(code_variations),
            course=course  # Include course context
        )
        
        # Progress is automatically updated via the PromptSubmission model's save method
        # Get the updated progress for response
        progress = UserProgress.objects.get(
            user=request.user,
            problem=problem,
            problem_set=problem_set,
            course=course
        )
        
        return Response({
            'submission_id': submission.id,
            'score': int(score),
            'variations': code_variations,  # Frontend expects 'variations'
            'results': all_results,  # Frontend expects 'results'
            'passing_variations': total_passed,
            'total_variations': len(code_variations),
            'progress': {
                'status': progress.status,
                'best_score': progress.best_score,
                'attempts': progress.attempts,
                'is_completed': progress.is_completed,
            }
        })