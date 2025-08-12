"""
Clean permission system for Purplex.
No debug bypasses, no backdoors - just proper permission checks.
"""
from rest_framework import permissions
from django.contrib.auth.models import User
from typing import Any


class IsAuthenticated(permissions.BasePermission):
    """
    Simple authenticated user check without any debug bypasses.
    """
    
    def has_permission(self, request, view) -> bool:
        return request.user and request.user.is_authenticated


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners to edit their own objects.
    Read permissions are allowed to any authenticated user.
    """
    
    def has_object_permission(self, request, view, obj) -> bool:
        # Read permissions for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        # Write permissions only for owner
        # Check various owner field names
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'owner'):
            return obj.owner == request.user
        elif hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        
        # Default deny
        return False


class IsInstructorOrAdmin(permissions.BasePermission):
    """
    Allow access to instructors and admins only.
    Works consistently across all environments.
    """
    
    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check user profile role if it exists
        if hasattr(request.user, 'userprofile'):
            role = request.user.userprofile.role
            return role in ['instructor', 'admin']
        
        # Fallback to Django admin status
        return request.user.is_staff or request.user.is_superuser


class IsAdmin(permissions.BasePermission):
    """
    Allow access to admin users only.
    """
    
    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check user profile for admin role
        if hasattr(request.user, 'userprofile'):
            return request.user.userprofile.role == 'admin'
        
        # Fallback to Django superuser status
        return request.user.is_superuser


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Allow write access to admin users only, read access to all authenticated users.
    """
    
    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Read permissions for all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions for admins only
        if hasattr(request.user, 'userprofile'):
            return request.user.userprofile.role == 'admin'
        
        return request.user.is_superuser


class IsInstructor(permissions.BasePermission):
    """
    Allow access to instructor users only.
    """
    
    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check user profile for instructor role
        if hasattr(request.user, 'userprofile'):
            role = request.user.userprofile.role
            return role in ['instructor', 'admin']
        
        # Fallback to Django staff status
        return request.user.is_staff or request.user.is_superuser


class IsInstructorOrReadOnly(permissions.BasePermission):
    """
    Allow write access to instructors, read access to all authenticated users.
    """
    
    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Read permissions for all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions for instructors
        if hasattr(request.user, 'userprofile'):
            role = request.user.userprofile.role
            return role in ['instructor', 'admin']
        
        return request.user.is_staff or request.user.is_superuser


class IsCourseInstructor(permissions.BasePermission):
    """
    Allow access only to the instructor of a specific course.
    """
    
    def has_object_permission(self, request, view, obj) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Handle different object types
        if hasattr(obj, 'instructor'):
            # Direct course object
            return obj.instructor == request.user or request.user.is_superuser
        elif hasattr(obj, 'course'):
            # Related to course (e.g., enrollment, problem set)
            return obj.course.instructor == request.user or request.user.is_superuser
        
        return False


class IsEnrolledInCourse(permissions.BasePermission):
    """
    Allow access only to students enrolled in a course.
    """
    
    def has_object_permission(self, request, view, obj) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Import here to avoid circular imports
        from purplex.problems_app.models import CourseEnrollment
        
        # Get the course from the object
        course = None
        if hasattr(obj, 'course'):
            course = obj.course
        elif hasattr(obj, 'courses'):
            # Handle objects that might belong to multiple courses
            # Check if user is enrolled in any of them
            for c in obj.courses.all():
                if CourseEnrollment.objects.filter(
                    user=request.user,
                    course=c,
                    is_active=True
                ).exists():
                    return True
            return False
        
        if course:
            # Check enrollment
            return CourseEnrollment.objects.filter(
                user=request.user,
                course=course,
                is_active=True
            ).exists()
        
        return False


class CanSubmitSolution(permissions.BasePermission):
    """
    Check if user can submit a solution for a problem.
    This includes checking course enrollment if applicable.
    """
    
    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Get problem and course from request
        problem_id = request.data.get('problem_id') or request.data.get('problem')
        course_id = request.data.get('course_id') or request.data.get('course')
        
        if not problem_id:
            return False  # No problem specified
        
        # If course is specified, check enrollment
        if course_id:
            from purplex.problems_app.models import Course, CourseEnrollment
            
            try:
                course = Course.objects.get(id=course_id)
                # Check if user is enrolled
                enrolled = CourseEnrollment.objects.filter(
                    user=request.user,
                    course=course,
                    is_active=True
                ).exists()
                
                # Instructors can also submit solutions to their own courses
                is_instructor = course.instructor == request.user
                
                return enrolled or is_instructor or request.user.is_superuser
            except Course.DoesNotExist:
                return False
        
        # No course specified - allow any authenticated user
        return True


class CanViewHint(permissions.BasePermission):
    """
    Check if user can view hints for a problem.
    May require minimum attempt count.
    """
    
    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admins can always view hints
        if request.user.is_superuser:
            return True
        
        # Check if hints are enabled globally
        from django.conf import settings
        if not getattr(settings, 'ENABLE_HINTS', True):
            return False
        
        return True
    
    def has_object_permission(self, request, view, obj) -> bool:
        """Check if user has made enough attempts to unlock this hint."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admins bypass attempt requirements
        if request.user.is_superuser:
            return True
        
        # Import here to avoid circular imports
        from purplex.problems_app.models import UserProgress
        
        # Get the problem from the hint
        problem = obj.problem if hasattr(obj, 'problem') else None
        if not problem:
            return False
        
        # Check attempt count
        min_attempts = getattr(obj, 'min_attempts', 0)
        if min_attempts > 0:
            # Get user's progress on this problem
            progress = UserProgress.objects.filter(
                user=request.user,
                problem=problem
            ).first()
            
            if not progress or progress.attempts < min_attempts:
                return False
        
        return True


class IsAuthenticatedOrServiceAccount(permissions.BasePermission):
    """
    Allow access to authenticated users or valid service accounts.
    Service accounts use X-Service-Key header.
    """
    
    def has_permission(self, request, view) -> bool:
        # Check regular authentication first
        if request.user and request.user.is_authenticated:
            return True
        
        # Check service account authentication
        service_key = request.META.get('HTTP_X_SERVICE_KEY')
        if service_key:
            import os
            valid_key = os.environ.get('SERVICE_ACCOUNT_KEY')
            return valid_key and service_key == valid_key
        
        return False


# Composite permissions for common use cases
class IsInstructorOrAdminOrOwner(permissions.BasePermission):
    """
    Allow instructors/admins full access, owners edit access, others read-only.
    """
    
    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Instructors and admins have full access
        if hasattr(request.user, 'userprofile'):
            role = request.user.userprofile.role
            if role in ['instructor', 'admin']:
                return True
        
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Others need object-level checks
        return True  # Will check in has_object_permission
    
    def has_object_permission(self, request, view, obj) -> bool:
        # Instructors and admins have full access
        if hasattr(request.user, 'userprofile'):
            role = request.user.userprofile.role
            if role in ['instructor', 'admin']:
                return True
        
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Read access for all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write access only for owners
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'owner'):
            return obj.owner == request.user
        
        return False