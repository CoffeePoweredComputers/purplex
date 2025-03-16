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
