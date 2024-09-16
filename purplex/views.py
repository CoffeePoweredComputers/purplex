from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.http import JsonResponse

from .models import PromptSubmission, Problem, ProblemSet
from .serializers import ProblemSerializer, ProblemSetSerializer

from rest_framework.views import APIView
from rest_framework.response import Response

import json
import docker
import openai
import os, subprocess

SERVER_URL = 'http://localhost:8000'
client = openai.OpenAI(
    api_key='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'
)

class ProblemListView(APIView):
    def get(self, request):
        problems = Problem.objects.all()
        serializer = ProblemSerializer(problems, many=True)
        return Response(serializer.data)
    
class ProblemSetListView(APIView):
    def get(self, request):
        problem_sets = ProblemSet.objects.all()
        serializer = ProblemSetSerializer(problem_sets, many=True)
        for problem_set, data in zip(problem_sets, serializer.data):
            data['icon'] = SERVER_URL + problem_set.icon.url
        return Response(serializer.data)

class GetProblemSet(APIView):
    def get(self, request, sid):
        try:
            problem_set = ProblemSet.objects.get(sid=sid)
        except ProblemSet.DoesNotExist:
            return Response({"error": "ProblemSet not found"}, status=404)
        
        serializer = ProblemSetSerializer(problem_set)
        data = serializer.data
        data['icon'] = problem_set.icon.url
        problems = problem_set.problems.all()
        problem_serializer = ProblemSerializer(problems, many=True)
        data['problems'] = problem_serializer.data
        
        return Response(data)

class AIView(APIView):
    CODE_SYSTEM_PROMPT = """
    Create five functions, each called foo, that are different implementation of a user's description.
    THe function should be interpretable by beginners and should use as few inbuilt function as
    possible.  For example, rather than using a built-in sum function to calculate the sum of a list,
    the code produced should write their own function to calculate the sum of a list. The returned code
    should be in the following format.  Using this format generate five different implementations of
    the user's input.  Note that the produced function has only as single function, rely on
    no outside or undefined helper functions, and no additional text, test case, or comments.

    ```
    def foo(<params here):
        <code here>
    ```
    ```
    def foo(<params here):
        <code here>
    ```
    ```
    def foo(<params here):
        <code here>
    ```
    ```
    def foo(<params here):
        <code here>
    ```
    ```
    def foo(<params here):
        <code here>
    ```

    Be sure to include the ``` and ``` at the beginning and end of the code block and name each
    function foo. Dont include the language in the markdown formating (e.g., ```python, ```c).
    The student's response is as follows:
    """  # truncated for brevity


    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        prompt = [
            {
                "role": "user", 
                "content":  self.CODE_SYSTEM_PROMPT + data.get('prompt')
            }
        ]

        response = client.chat.completions.create(
                model='gpt-4o',
                messages=prompt
        )

        generated_code = response.choices[0].message.content.replace("```python", "").replace("```", "").strip()
        return JsonResponse(generated_code, safe=False)

def run_test_script(code, input_data, expected_output):
    print("Running test script")
    print(f"Code: {code}")
    print(f"Input: {input_data}")
    print(f"Expected output: {expected_output}")

    result = subprocess.run(
        ['sh', 'src/pytest/test_script.sh', code, input_data, expected_output],
        capture_output=True,
        text=True
    )

    result_data = result.stdout.split(',')
    test_result = {
        'pass': result_data[0].strip() == 'correct',
        'func_call': result_data[1].strip(),
        'actual': result_data[2].strip(),
        'expected': result_data[3].strip()
    }

    print(f"Test result: {test_result}")
    return test_result

def test_view(request):
    # Assuming POST with JSON containing code, input, and expected output
    data = request.json()
    test_result = run_test_script(
        data['code'],
        data['input'],
        data['expected_output']
    )
    return JsonResponse(test_result)

#def run_eipl_autograder(submission_file_path, test_case_file_path):
#    client = docker.from_env()
#    try:
#        result = client.containers.run(
#            "your-docker-image",
#            volumes={
#                submission_file_path: {'bind': '/app/submission.py', 'mode': 'ro'},
#                test_case_file_path: {'bind': '/app/test_cases.py', 'mode': 'ro'}
#            },
#            working_dir='/app',
#            remove=True,
#            stdout=True,
#            stderr=True,
#            mem_limit='256m',  # Memory limit
#            cpus=1,            # CPU limit
#            network_disabled=True  # Disable network access
#        )
#        return result.decode('utf-8')
#    except docker.errors.ContainerError as e:
#        return str(e)
#
#def prompt_submission_result(request, submission_id):
#    submission = get_object_or_404(PromptSubmission, id=submission_id)
#    return render(request, 'submission_result.html', {'submission': submission})
#
def submit_code(request, problem_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        code = data.get('code', '')
        
        problem = get_object_or_404(Problem, id=problem_id)
        submission = PromptSubmission.objects.create(
            student=request.user,
            problem=problem,
            submission_time=timezone.now(),
        )

        submission_file_path = f'submissions/{submission.id}_submission.py'
        with open(submission_file_path, 'w') as submission_file:
            submission_file.write(code)
        
        result = run_eipl_autograder(submission_file_path, problem.test_case_file.path)
        submission.result = result
        submission.save()

        return JsonResponse({'result': result})
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=400)

