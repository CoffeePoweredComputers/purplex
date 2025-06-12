from rest_framework import permissions
from django.conf import settings
from .models import UserProfile, UserRole

# Debug mode flag to bypass strict permission checks during development
# This directly uses settings.DEBUG to control permission bypassing
DEBUG_BYPASS_PERMISSIONS = settings.DEBUG


class IsAuthenticated(permissions.BasePermission):
    """
    Custom permission to only allow authenticated users access.
    """
    def has_permission(self, request, view):
        if DEBUG_BYPASS_PERMISSIONS:
            return True

        return request.user.is_authenticated

class IsAdmin(permissions.BasePermission):
    """
    Custom permission to only allow admin users access.
    """
    def has_permission(self, request, view):
        if DEBUG_BYPASS_PERMISSIONS:
            return True

        # Allow GET requests for all authenticated users
        if request.method in permissions.SAFE_METHODS and request.user.is_authenticated:
            return True

        # Check if user is authenticated and has admin role
        if request.user.is_authenticated:
            try:
                profile = UserProfile.objects.get(user=request.user)
                return profile.role == UserRole.ADMIN
            except UserProfile.DoesNotExist:
                return False
        return False

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow read-only access to all users,
    but only allow write operations for admin users.
    """
    def has_permission(self, request, view):
        # Debug bypass for development
        if DEBUG_BYPASS_PERMISSIONS:
            return True

        # Allow GET, HEAD or OPTIONS requests for all authenticated users
        if request.method in permissions.SAFE_METHODS and request.user.is_authenticated:
            return True

        # Check if user is authenticated and has admin role for write operations
        if request.user.is_authenticated:
            try:
                profile = UserProfile.objects.get(user=request.user)
                return profile.role == UserRole.ADMIN
            except UserProfile.DoesNotExist:
                return False
        return False


class IsInstructor(permissions.BasePermission):
    """
    Custom permission to only allow instructors and admins access.
    Initially view-only for instructors.
    """
    def has_permission(self, request, view):
        if DEBUG_BYPASS_PERMISSIONS:
            return True

        if request.user.is_authenticated:
            try:
                profile = UserProfile.objects.get(user=request.user)
                return profile.role in [UserRole.INSTRUCTOR, UserRole.ADMIN]
            except UserProfile.DoesNotExist:
                return False
        return False


class IsCourseInstructor(permissions.BasePermission):
    """
    Custom permission to check if user is the instructor of a specific course.
    Admins always have access.
    """
    def has_permission(self, request, view):
        if DEBUG_BYPASS_PERMISSIONS:
            return True

        if not request.user.is_authenticated:
            return False

        try:
            profile = UserProfile.objects.get(user=request.user)
            # Admins always have access
            if profile.role == UserRole.ADMIN:
                return True
            # Instructors need to be checked per course
            return profile.role == UserRole.INSTRUCTOR
        except UserProfile.DoesNotExist:
            return False

    def has_object_permission(self, request, view, obj):
        """Check if user is instructor of the specific course"""
        if DEBUG_BYPASS_PERMISSIONS:
            return True

        if not request.user.is_authenticated:
            return False

        try:
            profile = UserProfile.objects.get(user=request.user)
            # Admins always have access
            if profile.role == UserRole.ADMIN:
                return True
            
            # For instructors, check if they own the course
            if profile.role == UserRole.INSTRUCTOR:
                # Handle different object types
                from purplex.problems_app.models import Course
                if isinstance(obj, Course):
                    return obj.instructor == request.user
                # Add more object type checks as needed
                
            return False
        except UserProfile.DoesNotExist:
            return False


class IsInstructorOrReadOnly(permissions.BasePermission):
    """
    Allow read access to all authenticated users,
    but only instructors/admins can modify.
    """
    def has_permission(self, request, view):
        if DEBUG_BYPASS_PERMISSIONS:
            return True

        # Allow read for all authenticated users
        if request.method in permissions.SAFE_METHODS and request.user.is_authenticated:
            return True

        # Write operations require instructor/admin role
        if request.user.is_authenticated:
            try:
                profile = UserProfile.objects.get(user=request.user)
                return profile.role in [UserRole.INSTRUCTOR, UserRole.ADMIN]
            except UserProfile.DoesNotExist:
                return False
        return False
