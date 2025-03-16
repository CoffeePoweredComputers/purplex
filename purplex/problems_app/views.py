from django.shortcuts import render
from django.http import JsonResponse

from .models import Problem, ProblemSet
from .serializers import ProblemSerializer, ProblemSetSerializer

from rest_framework.views import APIView
from rest_framework.response import Response
from purplex.users_app.permissions import IsAdmin, IsAdminOrReadOnly, IsAuthenticated
from rest_framework.decorators import permission_classes

import json

SERVER_URL = 'http://localhost:8000'

class ProblemListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        problems = Problem.objects.all()
        serializer = ProblemSerializer(problems, many=True)
        # return response with auth
        return Response(serializer.data)


class ProblemSetListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        problem_sets = ProblemSet.objects.all()
        serializer = ProblemSetSerializer(problem_sets, many=True)
        for problem_set, data in zip(problem_sets, serializer.data):
            data['icon'] = SERVER_URL + problem_set.icon.url
        return Response(serializer.data)

class GetProblemSet(APIView):
    permission_classes = [IsAuthenticated]
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

class AdminProblemView(APIView):
    permission_classes = [IsAdmin]
    
    def post(self, request):
        """Create a new problem (admin only)"""
        serializer = ProblemSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)
    
    def put(self, request, qid):
        """Update a problem (admin only)"""
        try:
            problem = Problem.objects.get(qid=qid)
        except Problem.DoesNotExist:
            return Response({"error": "Problem not found"}, status=404)
            
        serializer = ProblemSerializer(problem, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
    
    def delete(self, request, qid):
        """Delete a problem (admin only)"""
        try:
            problem = Problem.objects.get(qid=qid)
        except Problem.DoesNotExist:
            return Response({"error": "Problem not found"}, status=404)
            
        problem.delete()
        return Response(status=204)

class AdminProblemSetView(APIView):
    permission_classes = [IsAdmin]
    
    def post(self, request):
        """Create a new problem set (admin only)"""
        # Print request data for debugging
        print("Request data:", request.data)
        
        # Handle multipart form data
        data = {
            'title': request.data.get('title'),
            'sid': request.data.get('sid'),
            'problems': [],  # Initialize with empty array
        }
        
        # Handle file upload separately
        if 'icon' in request.FILES:
            data['icon'] = request.FILES['icon']
        
        serializer = ProblemSetSerializer(data=data)
        if serializer.is_valid():
            problem_set = serializer.save()
            # Create the response with the full URL
            response_data = serializer.data
            response_data['icon'] = SERVER_URL + problem_set.icon.url if problem_set.icon else None
            return Response(response_data, status=201)
        
        # Print validation errors
        print("Validation errors:", serializer.errors)
        return Response(serializer.errors, status=400)
    
    def put(self, request, sid):
        """Update a problem set (admin only)"""
        try:
            problem_set = ProblemSet.objects.get(sid=sid)
        except ProblemSet.DoesNotExist:
            return Response({"error": "ProblemSet not found"}, status=404)
            
        serializer = ProblemSetSerializer(problem_set, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
    
    def delete(self, request, sid):
        """Delete a problem set (admin only)"""
        try:
            problem_set = ProblemSet.objects.get(sid=sid)
        except ProblemSet.DoesNotExist:
            return Response({"error": "ProblemSet not found"}, status=404)
            
        problem_set.delete()
        return Response(status=204)
