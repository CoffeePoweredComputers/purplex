from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from django.db import models
from rest_framework.views import APIView
from rest_framework.response import Response
from purplex.users_app.permissions import IsAdmin, IsAdminOrReadOnly, IsAuthenticated

import json
import docker

from .models import PromptSubmission
from purplex.problems_app.models import Problem

class PythonTestView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        data = request.data
        generated_code = data.get('generated_code')
        qid = data.get('qid')

        problem = Problem.objects.get(qid=qid)
        test_cases_file = problem.test_case_file.path.split('/')[-1]
        test_case_file_path = problem.test_case_file.path

        client = docker.from_env()
        result = client.containers.run(
                "coffeepwrdcomputers/eiplgrader:latest",
                environment={
                    "USER_CODE": generated_code,
                    "TEST_CASES_FILE": test_cases_file
                },
                volumes={
                    test_case_file_path: {'bind': f"/app/{test_cases_file}", 'mode': 'ro'}
                },
                working_dir='/app',
                remove=True,
                stdout=True,
                stderr=True,
                mem_limit='256m',  
                network_disabled=True
            )
        results = json.loads(result)

        return JsonResponse({"test_results": results})

class PromptSubmissionResultView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, submission_id):
        # Get the submission
        submission = get_object_or_404(PromptSubmission, id=submission_id)
        
        # Check if user is admin or the owner of this submission
        if request.user == submission.user or hasattr(request.user, 'profile') and request.user.profile.is_admin:
            return render(request, 'submission_result.html', {'submission': submission})
        else:
            return JsonResponse({'error': 'Permission denied'}, status=403)

class SubmitCodeView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, problem_id):
        data = json.loads(request.body)
        code = data.get('code', '')
        
        problem = get_object_or_404(Problem, id=problem_id)
        submission = PromptSubmission.objects.create(
            user=request.user,
            problem=problem,
            score=0,  # Initial score
            prompt=code
        )

        # Test the code using Docker
        client = docker.from_env()
        test_cases_file = problem.test_case_file.path.split('/')[-1]
        test_case_file_path = problem.test_case_file.path
        
        result = client.containers.run(
            "coffeepwrdcomputers/eiplgrader:latest",
            environment={
                "USER_CODE": code,
                "TEST_CASES_FILE": test_cases_file
            },
            volumes={
                test_case_file_path: {'bind': f"/app/{test_cases_file}", 'mode': 'ro'}
            },
            working_dir='/app',
            remove=True,
            stdout=True,
            stderr=True,
            mem_limit='256m',  
            network_disabled=True
        )
        
        results = json.loads(result)
        
        # Update score based on test results
        passed_tests = sum(1 for test in results if test.get('pass', False))
        total_tests = len(results)
        if total_tests > 0:
            submission.score = int((passed_tests / total_tests) * 100)
            submission.save()

        return JsonResponse({'results': results})

class AdminSubmissionsView(APIView):
    """View for admin users to manage submissions"""
    permission_classes = [IsAdmin]
    
    def get(self, request):
        """List all submissions (admin only)"""
        submissions = PromptSubmission.objects.all().select_related('user', 'problem', 'problem_set')
        
        submissions_data = []
        for submission in submissions:
            # Calculate status based on score
            if submission.score >= 80:
                status = 'passed'
            elif submission.score > 0:
                status = 'partial'
            else:
                status = 'failed'
                
            submissions_data.append({
                'id': submission.id,
                'user': submission.user.username,  # Changed from 'username'
                'problem': submission.problem.title,
                'problem_set': submission.problem_set.title if submission.problem_set else 'Unknown',
                'score': submission.score,
                'status': status,  # Added missing status
                'created_at': submission.time,  # Changed from 'submitted_at'
            })
            
        return Response(submissions_data)
        
    def delete(self, request, submission_id):
        """Delete a submission (admin only)"""
        submission = get_object_or_404(PromptSubmission, id=submission_id)
        submission.delete()
        return Response(status=204)

class AdminSubmissionExportView(APIView):
    """Export submissions data for CSV download (admin only)"""
    permission_classes = [IsAdmin]
    
    def post(self, request):
        """Get detailed submission data for CSV export"""
        filters = request.data.get('filters', {})
        
        # Start with all submissions
        submissions = PromptSubmission.objects.all().select_related('user', 'problem', 'problem_set')
        
        # Apply filters
        search_query = filters.get('search', '').strip().lower()
        if search_query:
            submissions = submissions.filter(
                models.Q(user__username__icontains=search_query) |
                models.Q(problem__title__icontains=search_query) |
                models.Q(problem_set__title__icontains=search_query)
            )
        
        status_filter = filters.get('status', '').strip()
        if status_filter:
            # Filter by score ranges based on status
            if status_filter == 'passed':
                submissions = submissions.filter(score__gte=80)
            elif status_filter == 'partial':
                submissions = submissions.filter(score__gt=0, score__lt=80)
            elif status_filter == 'failed':
                submissions = submissions.filter(score=0)
        
        problem_set_filter = filters.get('problem_set', '').strip()
        if problem_set_filter:
            submissions = submissions.filter(problem_set__title=problem_set_filter)
        
        # Prepare detailed data for export
        export_data = []
        for submission in submissions:
            # Calculate status
            if submission.score >= 80:
                status = 'passed'
            elif submission.score > 0:
                status = 'partial'
            else:
                status = 'failed'
            
            export_data.append({
                'id': submission.id,
                'user': submission.user.username,
                'problem': submission.problem.title,
                'problem_set': submission.problem_set.title if submission.problem_set else 'Unknown',
                'score': submission.score,
                'status': status,
                'created_at': submission.time.isoformat() if submission.time else '',
                'user_solution': submission.user_solution or '',
                'feedback': submission.feedback or '',
                'prompt': submission.prompt or ''
            })
        
        return Response(export_data)

class AdminSubmissionDetailView(APIView):
    """Get detailed data for a single submission (admin only)"""
    permission_classes = [IsAdmin]
    
    def get(self, request, submission_id):
        """Get full submission details including user solution and feedback"""
        submission = get_object_or_404(PromptSubmission, id=submission_id)
        
        # Calculate status
        if submission.score >= 80:
            status = 'passed'
        elif submission.score > 0:
            status = 'partial'
        else:
            status = 'failed'
        
        submission_data = {
            'id': submission.id,
            'user': submission.user.username,
            'problem': submission.problem.title,
            'problem_set': submission.problem_set.title if submission.problem_set else 'Unknown',
            'score': submission.score,
            'status': status,
            'created_at': submission.time.isoformat() if submission.time else '',
            'user_solution': submission.user_solution or '',
            'feedback': submission.feedback or '',
            'prompt': submission.prompt or ''
        }
        
        return Response(submission_data)

class UserLastSubmissionView(APIView):
    """Get user's most recent submission for a specific problem"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, problem_slug):
        """Get the user's most recent submission for this problem"""
        try:
            # Debug logging
            print(f"Looking for submissions for user: {request.user.username}, problem_slug: {problem_slug}")
            
            # Check if problem exists
            from purplex.problems_app.models import Problem
            problem = Problem.objects.filter(slug=problem_slug).first()
            if not problem:
                print(f"Problem not found with slug: {problem_slug}")
                return Response({'has_submission': False, 'error': f'Problem not found: {problem_slug}'})
            
            print(f"Problem found: {problem.title}")
            
            # Get the user's most recent submission for this problem
            submission = PromptSubmission.objects.filter(
                user=request.user,
                problem=problem
            ).select_related('problem', 'problem_set').order_by('-time').first()
            
            print(f"Submissions found: {PromptSubmission.objects.filter(user=request.user, problem=problem).count()}")
            
            if not submission:
                print("No submission found for this user and problem")
                return Response({'has_submission': False})
            
            print(f"Latest submission found: ID {submission.id}, Score: {submission.score}")
            print(f"Raw user_solution: {submission.user_solution}")
            print(f"Type of user_solution: {type(submission.user_solution)}")
            
            # Parse the user_solution JSON data
            user_solution_data = submission.user_solution or {}
            
            # Handle case where user_solution might be a string instead of dict
            if isinstance(user_solution_data, str):
                try:
                    import json
                    user_solution_data = json.loads(user_solution_data)
                except json.JSONDecodeError:
                    print(f"Failed to parse user_solution as JSON: {user_solution_data}")
                    user_solution_data = {}
            
            # Also try to parse feedback field which might contain the actual data
            feedback_data = {}
            if submission.feedback:
                try:
                    import json
                    feedback_data = json.loads(submission.feedback)
                    print(f"Parsed feedback data: {feedback_data}")
                except json.JSONDecodeError:
                    print(f"Feedback is not JSON: {submission.feedback}")
            
            # Use standard field names: variations, results, passing_variations
            variations = user_solution_data.get('variations', [])
            results = user_solution_data.get('results', [])
            
            # Calculate passing variations from the test results
            passing_variations = 0
            if results:
                for result_set in results:
                    if isinstance(result_set, list) and all(test.get('pass', False) for test in result_set):
                        passing_variations += 1
            
            print(f"Final data - Variations: {len(variations)}, Results: {len(results)}, Passing: {passing_variations}")
            
            return Response({
                'has_submission': True,
                'submission_id': submission.id,
                'score': submission.score,
                'variations': variations,
                'results': results,
                'passing_variations': passing_variations,
                'submitted_at': submission.time.isoformat() if submission.time else None,
                'feedback': submission.feedback
            })
            
        except Exception as e:
            print(f"Error in UserLastSubmissionView: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=500)
