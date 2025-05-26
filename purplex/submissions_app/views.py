from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
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
        submissions = PromptSubmission.objects.all().select_related('user', 'problem')
        
        submissions_data = []
        for submission in submissions:
            submissions_data.append({
                'id': submission.id,
                'problem': submission.problem.title,
                'username': submission.user.username,
                'score': submission.score,
                'submitted_at': submission.time,
            })
            
        return Response(submissions_data)
        
    def delete(self, request, submission_id):
        """Delete a submission (admin only)"""
        submission = get_object_or_404(PromptSubmission, id=submission_id)
        submission.delete()
        return Response(status=204)
