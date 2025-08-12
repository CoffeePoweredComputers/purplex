from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .permissions import IsAdmin, IsAuthenticated
from django.conf import settings

import json
import os
import openai

from django.contrib.auth.models import User
from .models import UserProfile, UserRole
from .authentication import FirebaseAuthentication

# Get API key and model from settings
client = openai.OpenAI(
    api_key=os.environ.get('OPENAI_API_KEY', '')
)
GPT_MODEL = getattr(settings, 'GPT_MODEL', 'gpt-4o-mini')

class AIGenerateView(APIView):
    permission_classes = [IsAuthenticated]
    
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
    """  

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
                model=GPT_MODEL,
                messages=prompt
        )

        generated_code = list(map(lambda x: x.replace("```", "").strip(), response.choices[0].message.content.split("```")[1::2]))
        return JsonResponse({"code": generated_code}, safe=False)

class UserRoleView(APIView):
    """View for getting current user's role"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
            return Response({
                'username': request.user.username,
                'email': request.user.email,
                'role': profile.role,
                'is_admin': profile.is_admin,
                'firebase_uid': profile.firebase_uid
            })
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found'}, status=404)
            
class AuthStatusView(APIView):
    """View for validating a Firebase token and returning user information"""
    
    def post(self, request):
        auth = FirebaseAuthentication()
        
        # Try to authenticate with the provided token
        try:
            user_auth_tuple = auth.authenticate(request)
            if user_auth_tuple is None:
                return Response({'authenticated': False, 'message': 'Invalid authentication token'}, status=401)
                
            user, _ = user_auth_tuple
            
            # Get user profile
            try:
                profile = UserProfile.objects.get(user=user)
                return Response({
                    'authenticated': True,
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'role': profile.role,
                        'is_admin': profile.is_admin,
                        'firebase_uid': profile.firebase_uid
                    }
                })
            except UserProfile.DoesNotExist:
                return Response({'authenticated': False, 'message': 'User profile not found'}, status=404)
                
        except Exception as e:
            return Response({'authenticated': False, 'message': str(e)}, status=401)

class AdminUserManagementView(APIView):
    """View for admin users to manage other users' roles"""
    permission_classes = [IsAdmin]
    
    def get(self, request):
        """List all users and their roles (admin only)"""
        users = User.objects.all()

        if settings.DEBUG and not UserProfile.objects.exists():
            print("Debug mode: Creating test user profiles")
            for user in users:
                # Check if profile already exists
                if not hasattr(user, 'profile'):
                    UserProfile.objects.create(
                        user=user,
                        firebase_uid=f"debug_firebase_{user.id}",
                        role=UserRole.ADMIN if user.is_superuser else UserRole.USER
                    )

        user_profiles = UserProfile.objects.all().select_related('user')

        if user_profiles.exists():
            # Users with profiles exist, return them
            users_data = []
            for profile in user_profiles:
                users_data.append({
                    'id': profile.user.id,
                    'username': profile.user.username,
                    'email': profile.user.email,
                    'role': profile.role,
                    'is_active': profile.user.is_active
                })
            return Response(users_data)
        
        # No profiles exist, return users with default roles
        users_data = []
        for user in users:
            users_data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': 'user',  # Default role
                'is_active': user.is_active
            })
        return Response(users_data)

    def post(self, request, user_id):
        """Update a user's role (admin only)"""
        user = get_object_or_404(User, id=user_id)

        try:
            profile = UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            # Create profile if it doesn't exist
            profile = UserProfile.objects.create(
                user=user,
                firebase_uid=f"firebase_{user.id}",  # Temporary Firebase UID
                role=UserRole.USER
            )

        role = request.data.get('role')
        if role not in [UserRole.ADMIN, UserRole.INSTRUCTOR, UserRole.USER]:
            return Response({'error': 'Invalid role'}, status=400)

        profile.role = role
        profile.save()

        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': profile.role
        })
