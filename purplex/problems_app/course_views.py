"""
Course management views for the Purplex platform
"""
import logging
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Count, Q, Prefetch, Max
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Course, CourseEnrollment, CourseProblemSet, ProblemSet, UserProgress, UserProblemSetProgress
from .serializers import (
    CourseListSerializer, CourseDetailSerializer, CourseCreateUpdateSerializer,
    CourseEnrollmentSerializer, CourseLookupSerializer, CourseEnrollSerializer,
    ProblemSetListSerializer
)
from django.contrib.auth.models import User
from purplex.users_app.permissions import IsAdmin, IsInstructor, IsCourseInstructor, IsInstructorOrReadOnly
from purplex.users_app.models import UserProfile

logger = logging.getLogger(__name__)


# Admin-Only Course Management
class AdminCourseListCreateView(APIView):
    """Admin endpoint for listing and creating courses"""
    permission_classes = [IsAdmin]
    
    def get(self, request):
        """List all courses (including deleted for admins)"""
        courses = Course.objects.select_related('instructor').annotate(
            problem_sets_count=Count('problem_sets'),
            enrolled_students_count=Count('enrollments', filter=Q(enrollments__is_active=True))
        ).order_by('-created_at')
        
        # Filter by active status if requested
        if request.query_params.get('active_only') == 'true':
            courses = courses.filter(is_active=True, is_deleted=False)
        
        serializer = CourseListSerializer(courses, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        """Create a new course"""
        serializer = CourseCreateUpdateSerializer(data=request.data)
        if serializer.is_valid():
            # Set the instructor to the requesting user
            course = serializer.save(instructor=request.user)
            return Response(
                CourseDetailSerializer(course).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminCourseDetailView(APIView):
    """Admin endpoint for course details, updates, and deletion"""
    permission_classes = [IsAdmin]
    
    def get(self, request, course_id):
        """Get course details"""
        course = get_object_or_404(Course, course_id=course_id)
        serializer = CourseDetailSerializer(course)
        return Response(serializer.data)
    
    def put(self, request, course_id):
        """Update course details"""
        course = get_object_or_404(Course, course_id=course_id)
        serializer = CourseCreateUpdateSerializer(course, data=request.data, partial=True)
        if serializer.is_valid():
            course = serializer.save()
            return Response(CourseDetailSerializer(course).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, course_id):
        """Soft delete a course"""
        course = get_object_or_404(Course, course_id=course_id)
        course.soft_delete()
        return Response({'message': 'Course deleted successfully'}, status=status.HTTP_204_NO_CONTENT)


class AdminCourseProblemSetView(APIView):
    """Admin endpoint for managing problem sets in a course"""
    permission_classes = [IsAdmin]
    
    def post(self, request, course_id):
        """Add a problem set to a course"""
        course = get_object_or_404(Course, course_id=course_id)
        problem_set_id = request.data.get('problem_set_id')
        order = request.data.get('order', 0)
        is_required = request.data.get('is_required', True)
        
        try:
            problem_set = ProblemSet.objects.get(id=problem_set_id)
            course_ps, created = CourseProblemSet.objects.update_or_create(
                course=course,
                problem_set=problem_set,
                defaults={
                    'order': order,
                    'is_required': is_required,
                    'problem_set_version': problem_set.version
                }
            )
            return Response({
                'id': course_ps.id,
                'problem_set': ProblemSetListSerializer(problem_set).data,
                'order': course_ps.order,
                'is_required': course_ps.is_required
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        except ProblemSet.DoesNotExist:
            return Response({'error': 'Problem set not found'}, status=status.HTTP_404_NOT_FOUND)
    
    def delete(self, request, course_id, ps_id):
        """Remove a problem set from a course"""
        course = get_object_or_404(Course, course_id=course_id)
        CourseProblemSet.objects.filter(course=course, problem_set_id=ps_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Instructor Views (View-Only Initially)
class InstructorCourseListView(APIView):
    """List courses for an instructor"""
    permission_classes = [IsInstructor]
    
    def get(self, request):
        """List instructor's courses"""
        courses = Course.objects.filter(
            instructor=request.user,
            is_deleted=False
        ).annotate(
            problem_sets_count=Count('problem_sets'),
            enrolled_students_count=Count('enrollments', filter=Q(enrollments__is_active=True))
        ).order_by('-created_at')
        
        serializer = CourseListSerializer(courses, many=True)
        return Response(serializer.data)


class InstructorCourseDetailView(APIView):
    """Get course details for instructor"""
    permission_classes = [IsCourseInstructor]
    
    def get(self, request, course_id):
        """Get course details"""
        course = get_object_or_404(Course, course_id=course_id)
        # Check object-level permission
        self.check_object_permissions(request, course)
        
        serializer = CourseDetailSerializer(course)
        return Response(serializer.data)


class InstructorCourseStudentsView(APIView):
    """View enrolled students for a course"""
    permission_classes = [IsCourseInstructor]
    
    def get(self, request, course_id):
        """List enrolled students"""
        course = get_object_or_404(Course, course_id=course_id)
        self.check_object_permissions(request, course)
        
        enrollments = CourseEnrollment.objects.filter(
            course=course,
            is_active=True
        ).select_related('user__profile').order_by('-enrolled_at')
        
        serializer = CourseEnrollmentSerializer(enrollments, many=True)
        return Response(serializer.data)


class InstructorCourseProgressView(APIView):
    """View student progress in a course"""
    permission_classes = [IsCourseInstructor]
    
    def get(self, request, course_id):
        """Get all student progress for the course"""
        course = get_object_or_404(Course, course_id=course_id)
        self.check_object_permissions(request, course)
        
        # Get all enrolled students
        enrolled_users = course.enrollments.filter(is_active=True).values_list('user', flat=True)
        
        # Get progress for all problems in the course's problem sets
        progress_data = []
        for user_id in enrolled_users:
            user_progress = UserProgress.objects.filter(
                user_id=user_id,
                course=course
            ).select_related('user', 'problem', 'problem_set')
            
            # Aggregate by problem set
            problem_set_progress = {}
            for progress in user_progress:
                ps_id = progress.problem_set_id
                if ps_id not in problem_set_progress:
                    problem_set_progress[ps_id] = {
                        'problem_set': progress.problem_set.title,
                        'total_problems': progress.problem_set.problems.count(),
                        'completed_problems': 0,
                        'average_score': 0,
                        'scores': []
                    }
                
                if progress.is_completed:
                    problem_set_progress[ps_id]['completed_problems'] += 1
                problem_set_progress[ps_id]['scores'].append(progress.best_score)
            
            # Calculate averages
            for ps_data in problem_set_progress.values():
                if ps_data['scores']:
                    ps_data['average_score'] = sum(ps_data['scores']) / len(ps_data['scores'])
                del ps_data['scores']  # Remove raw scores from response
            
            progress_data.append({
                'user': {
                    'id': user_id,
                    'username': user_progress.first().user.username if user_progress else 'Unknown'
                },
                'problem_sets': list(problem_set_progress.values())
            })
        
        return Response(progress_data)


class InstructorCourseProblemSetOrderView(APIView):
    """Reorder problem sets in a course"""
    permission_classes = [IsCourseInstructor]
    
    def put(self, request, course_id):
        """Update problem set ordering"""
        course = get_object_or_404(Course, course_id=course_id)
        self.check_object_permissions(request, course)
        
        # Expect data like: [{"problem_set_id": 1, "order": 0}, ...]
        ordering_data = request.data.get('ordering', [])
        
        with transaction.atomic():
            for item in ordering_data:
                CourseProblemSet.objects.filter(
                    course=course,
                    problem_set_id=item['problem_set_id']
                ).update(order=item['order'])
        
        return Response({'message': 'Problem sets reordered successfully'})


# Student Course Views
class StudentEnrolledCoursesView(APIView):
    """List courses a student is enrolled in with full progress data"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get enrolled courses with embedded problem set progress"""
        # Single optimized query with all needed data
        enrollments = CourseEnrollment.objects.filter(
            user=request.user,
            is_active=True
        ).select_related('course__instructor').prefetch_related(
            Prefetch(
                'course__courseproblemset_set',
                queryset=CourseProblemSet.objects.select_related('problem_set').order_by('order')
            )
        )
        
        # Get all progress data in one query
        all_problem_set_ids = []
        for enrollment in enrollments:
            all_problem_set_ids.extend(enrollment.course.problem_sets.values_list('id', flat=True))
        
        progress_data = UserProblemSetProgress.objects.filter(
            user=request.user,
            problem_set_id__in=all_problem_set_ids,
            course__in=[e.course for e in enrollments]
        ).values('problem_set_id', 'course_id', 'completed_problems', 'total_problems', 'is_completed')
        
        # Build progress lookup
        progress_lookup = {}
        for p in progress_data:
            key = (p['course_id'], p['problem_set_id'])
            progress_lookup[key] = p
        
        courses_data = []
        for enrollment in enrollments:
            course = enrollment.course
            
            # Build problem sets with inline progress
            problem_sets_data = []
            completed_sets = 0
            
            for cps in course.courseproblemset_set.all():
                ps = cps.problem_set
                progress_key = (course.id, ps.id)
                progress = progress_lookup.get(progress_key, {})
                
                completed = progress.get('completed_problems', 0)
                total = progress.get('total_problems', ps.problems.count())
                is_completed = progress.get('is_completed', False)
                
                if is_completed:
                    completed_sets += 1
                
                problem_sets_data.append({
                    'problem_set': {
                        'slug': ps.slug,
                        'title': ps.title,
                        'description': ps.description,
                        'icon': ps.icon.url if ps.icon else None,
                        'problems_count': total
                    },
                    'progress': {
                        'completed_problems': completed,
                        'total_problems': total,
                        'percentage': int((completed / total * 100) if total > 0 else 0)
                    },
                    'order': cps.order,
                    'is_required': cps.is_required
                })
            
            total_sets = len(problem_sets_data)
            
            courses_data.append({
                'course': {
                    'course_id': course.course_id,
                    'name': course.name,
                    'description': course.description,
                    'instructor_name': course.instructor.get_full_name() or course.instructor.username,
                    'problem_sets': problem_sets_data
                },
                'enrolled_at': enrollment.enrolled_at,
                'progress': {
                    'completed_sets': completed_sets,
                    'total_sets': total_sets,
                    'percentage': int((completed_sets / total_sets * 100) if total_sets > 0 else 0)
                }
            })
        
        return Response(courses_data)


class CourseLookupView(APIView):
    """Lookup a course by ID for enrollment"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Lookup course details"""
        serializer = CourseLookupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        course_id = serializer.validated_data['course_id']
        
        try:
            course = Course.objects.get(
                course_id=course_id,
                is_active=True,
                is_deleted=False,
                enrollment_open=True
            )
            
            # Check if already enrolled
            is_enrolled = CourseEnrollment.objects.filter(
                user=request.user,
                course=course,
                is_active=True
            ).exists()
            
            return Response({
                'course': {
                    'course_id': course.course_id,
                    'name': course.name,
                    'description': course.description,
                    'instructor': course.instructor.get_full_name() or course.instructor.username,
                    'problem_sets_count': course.problem_sets.count(),
                    'enrollment_open': course.enrollment_open,
                },
                'already_enrolled': is_enrolled
            })
        except Course.DoesNotExist:
            return Response(
                {'error': 'Course not found or enrollment is closed'},
                status=status.HTTP_404_NOT_FOUND
            )


class CourseEnrollView(APIView):
    """Enroll in a course"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Enroll user in course"""
        serializer = CourseEnrollSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        course_id = serializer.validated_data['course_id']
        
        try:
            course = Course.objects.get(
                course_id=course_id,
                is_active=True,
                is_deleted=False,
                enrollment_open=True
            )
            
            # Check if already enrolled
            enrollment, created = CourseEnrollment.objects.get_or_create(
                user=request.user,
                course=course,
                defaults={'is_active': True}
            )
            
            if not created and enrollment.is_active:
                return Response(
                    {'error': 'You are already enrolled in this course'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            elif not created:
                # Reactivate enrollment
                enrollment.is_active = True
                enrollment.save()
            
            return Response({
                'success': True,
                'course': CourseDetailSerializer(course).data,
                'enrolled_at': enrollment.enrolled_at
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
            
        except Course.DoesNotExist:
            return Response(
                {'error': 'Course not found or enrollment is closed'},
                status=status.HTTP_404_NOT_FOUND
            )


class StudentCourseDetailView(APIView):
    """Get course details for enrolled students"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id):
        """Get course with problem sets"""
        course = get_object_or_404(Course, course_id=course_id, is_active=True, is_deleted=False)
        
        # Check enrollment
        if not CourseEnrollment.objects.filter(
            user=request.user,
            course=course,
            is_active=True
        ).exists():
            return Response(
                {'error': 'You are not enrolled in this course'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = CourseDetailSerializer(course)
        return Response(serializer.data)


class StudentCourseProgressView(APIView):
    """Get student's own progress in a course"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id):
        """Get progress for the requesting user"""
        course = get_object_or_404(Course, course_id=course_id)
        
        # Check enrollment
        if not CourseEnrollment.objects.filter(
            user=request.user,
            course=course,
            is_active=True
        ).exists():
            return Response(
                {'error': 'You are not enrolled in this course'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get progress for all problem sets in the course
        problem_set_ids = course.problem_sets.values_list('id', flat=True)
        progress_data = UserProblemSetProgress.objects.filter(
            user=request.user,
            problem_set_id__in=problem_set_ids
        ).select_related('problem_set')
        
        # Create a map of progress
        progress_map = {p.problem_set_id: p for p in progress_data}
        
        # Build response with all problem sets
        response_data = []
        for cps in course.courseproblemset_set.select_related('problem_set').order_by('order'):
            ps = cps.problem_set
            progress = progress_map.get(ps.id)
            
            response_data.append({
                'problem_set': {
                    'id': ps.id,
                    'slug': ps.slug,
                    'title': ps.title
                },
                'order': cps.order,
                'is_required': cps.is_required,
                'progress': {
                    'completed_problems': progress.completed_problems if progress else 0,
                    'total_problems': progress.total_problems if progress else ps.problems.count(),
                    'percentage': progress.completion_percentage if progress else 0,
                    'is_completed': progress.is_completed if progress else False,
                    'last_activity': progress.last_activity if progress else None
                } if progress else None
            })
        
        return Response(response_data)


# New Admin Views for Course Action Buttons

class AdminCourseProblemSetsView(APIView):
    """Admin endpoint for managing problem sets in a course"""
    permission_classes = [IsAdmin]
    
    def get(self, request, course_id):
        """Get all problem sets assigned to a course"""
        course = get_object_or_404(Course, course_id=course_id)
        
        # Get problem sets with their order and required status
        course_problem_sets = CourseProblemSet.objects.filter(
            course=course
        ).select_related('problem_set').order_by('order')
        
        response_data = []
        for cps in course_problem_sets:
            response_data.append({
                'id': cps.id,
                'problem_set': {
                    'slug': cps.problem_set.slug,
                    'title': cps.problem_set.title,
                    'problems_count': cps.problem_set.problems.count()
                },
                'order': cps.order,
                'is_required': cps.is_required,
                'added_at': cps.added_at
            })
        
        return Response(response_data)
    
    def post(self, request, course_id):
        """Add a problem set to a course"""
        course = get_object_or_404(Course, course_id=course_id)
        problem_set_slug = request.data.get('problem_set_slug')
        is_required = request.data.get('is_required', False)
        order = request.data.get('order')
        
        if not problem_set_slug:
            return Response(
                {'error': 'problem_set_slug is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            problem_set = ProblemSet.objects.get(slug=problem_set_slug)
            
            # Check if already in course
            if CourseProblemSet.objects.filter(course=course, problem_set=problem_set).exists():
                return Response(
                    {'error': 'Problem set is already in this course'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Auto-assign order if not provided
            if order is None:
                max_order = CourseProblemSet.objects.filter(course=course).aggregate(
                    max_order=Max('order')
                )['max_order'] or -1
                order = max_order + 1
            
            course_ps = CourseProblemSet.objects.create(
                course=course,
                problem_set=problem_set,
                order=order,
                is_required=is_required,
                problem_set_version=problem_set.version
            )
            
            return Response({
                'id': course_ps.id,
                'problem_set': {
                    'slug': problem_set.slug,
                    'title': problem_set.title,
                    'problems_count': problem_set.problems.count()
                },
                'order': course_ps.order,
                'is_required': course_ps.is_required,
                'added_at': course_ps.added_at
            }, status=status.HTTP_201_CREATED)
            
        except ProblemSet.DoesNotExist:
            return Response(
                {'error': 'Problem set not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def put(self, request, course_id, problem_set_slug):
        """Update problem set order or required status in course"""
        course = get_object_or_404(Course, course_id=course_id)
        
        try:
            course_ps = CourseProblemSet.objects.get(
                course=course,
                problem_set__slug=problem_set_slug
            )
            
            # Update fields if provided
            if 'order' in request.data:
                course_ps.order = request.data['order']
            if 'is_required' in request.data:
                course_ps.is_required = request.data['is_required']
            
            course_ps.save()
            
            return Response({
                'id': course_ps.id,
                'order': course_ps.order,
                'is_required': course_ps.is_required
            })
            
        except CourseProblemSet.DoesNotExist:
            return Response(
                {'error': 'Problem set not found in this course'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def delete(self, request, course_id, problem_set_slug):
        """Remove a problem set from a course"""
        course = get_object_or_404(Course, course_id=course_id)
        
        deleted_count = CourseProblemSet.objects.filter(
            course=course,
            problem_set__slug=problem_set_slug
        ).delete()[0]
        
        if deleted_count == 0:
            return Response(
                {'error': 'Problem set not found in this course'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminAvailableProblemSetsView(APIView):
    """Get problem sets not assigned to a specific course"""
    permission_classes = [IsAdmin]
    
    def get(self, request):
        """List problem sets available to add to a course"""
        exclude_course_id = request.query_params.get('exclude_course')
        
        # Start with all active problem sets
        available_problem_sets = ProblemSet.objects.filter(is_public=True)
        
        # Exclude those already in the specified course
        if exclude_course_id:
            assigned_ps_ids = CourseProblemSet.objects.filter(
                course__course_id=exclude_course_id
            ).values_list('problem_set_id', flat=True)
            available_problem_sets = available_problem_sets.exclude(id__in=assigned_ps_ids)
        
        # Order by title
        available_problem_sets = available_problem_sets.order_by('title')
        
        response_data = []
        for ps in available_problem_sets:
            response_data.append({
                'slug': ps.slug,
                'title': ps.title,
                'problems_count': ps.problems.count(),
                'description': ps.description
            })
        
        return Response(response_data)


class AdminCourseStudentsView(APIView):
    """Admin endpoint for managing students in a course"""
    permission_classes = [IsAdmin]
    
    def get(self, request, course_id):
        """Get all students enrolled in a course with progress info"""
        course = get_object_or_404(Course, course_id=course_id)
        
        enrollments = CourseEnrollment.objects.filter(
            course=course,
            is_active=True
        ).select_related('user__profile').order_by('-enrolled_at')
        
        response_data = []
        for enrollment in enrollments:
            user = enrollment.user
            
            # Get progress summary for this user in this course
            problem_set_ids = course.problem_sets.values_list('id', flat=True)
            user_progress = UserProblemSetProgress.objects.filter(
                user=user,
                problem_set_id__in=problem_set_ids
            )
            
            completed_count = user_progress.filter(is_completed=True).count()
            total_count = course.problem_sets.count()
            
            response_data.append({
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name
                },
                'enrolled_at': enrollment.enrolled_at,
                'is_active': enrollment.is_active,
                'progress': {
                    'completed_problem_sets': completed_count,
                    'total_problem_sets': total_count,
                    'completion_percentage': int((completed_count / total_count * 100) if total_count > 0 else 0)
                }
            })
        
        return Response(response_data)
    
    def delete(self, request, course_id, user_id):
        """Remove a student from a course"""
        course = get_object_or_404(Course, course_id=course_id)
        
        try:
            enrollment = CourseEnrollment.objects.get(
                course=course,
                user_id=user_id,
                is_active=True
            )
            # Soft delete - just mark as inactive
            enrollment.is_active = False
            enrollment.save()
            
            return Response(
                {'message': 'Student removed from course successfully'},
                status=status.HTTP_204_NO_CONTENT
            )
            
        except CourseEnrollment.DoesNotExist:
            return Response(
                {'error': 'Student not enrolled in this course'},
                status=status.HTTP_404_NOT_FOUND
            )