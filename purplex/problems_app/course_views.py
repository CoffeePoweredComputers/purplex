"""
Course management views for the Purplex platform
"""
import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .services.course_service import CourseService
from .serializers import (
    CourseListSerializer, CourseDetailSerializer, CourseCreateUpdateSerializer,
    CourseEnrollmentSerializer, CourseLookupSerializer, CourseEnrollSerializer,
    ProblemSetListSerializer
)
from purplex.users_app.permissions import IsAdmin, IsInstructor, IsCourseInstructor, IsInstructorOrReadOnly

logger = logging.getLogger(__name__)


# Admin-Only Course Management
class AdminInstructorsListView(APIView):
    """Admin endpoint for listing users who can be instructors"""
    permission_classes = [IsAdmin]

    def get(self, request):
        """List all users who can be assigned as instructors"""
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # Get all active users (admins and instructors)
        users = User.objects.filter(is_active=True).order_by('username')

        user_list = [
            {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.get_full_name() or user.username,
                'is_staff': user.is_staff,
            }
            for user in users
        ]

        return Response(user_list)


class AdminCourseListCreateView(APIView):
    """Admin endpoint for listing and creating courses"""
    permission_classes = [IsAdmin]

    def get(self, request):
        """List all courses (including deleted for admins)"""
        active_only = request.query_params.get('active_only') == 'true'

        if active_only:
            courses = CourseService.get_active_courses_with_stats()
        else:
            courses = CourseService.get_all_courses_with_stats()

        serializer = CourseListSerializer(courses, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        """Create a new course"""
        serializer = CourseCreateUpdateSerializer(data=request.data)
        if serializer.is_valid():
            # Get instructor from instructor_id or default to current user
            instructor_id = serializer.validated_data.pop('instructor_id', None)
            if instructor_id:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    instructor = User.objects.get(id=instructor_id)
                except User.DoesNotExist:
                    return Response(
                        {'error': 'Instructor not found'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                instructor = request.user

            # Use service layer to create course
            course = CourseService.create_course(
                instructor=instructor,
                **serializer.validated_data
            )
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
        course = CourseService.get_course_by_id(course_id, require_active=False)
        if not course:
            return Response(
                {'error': 'Course not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = CourseDetailSerializer(course)
        return Response(serializer.data)
    
    def put(self, request, course_id):
        """Update course details"""
        course = CourseService.get_course_by_id(course_id, require_active=False)
        if not course:
            return Response(
                {'error': 'Course not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = CourseCreateUpdateSerializer(course, data=request.data, partial=True)
        if serializer.is_valid():
            # Handle instructor update if provided
            instructor_id = serializer.validated_data.pop('instructor_id', None)
            if instructor_id:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    instructor = User.objects.get(id=instructor_id)
                    serializer.validated_data['instructor'] = instructor
                except User.DoesNotExist:
                    return Response(
                        {'error': 'Instructor not found'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            updated_course = CourseService.update_course(course, **serializer.validated_data)
            return Response(CourseDetailSerializer(updated_course).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, course_id):
        """Soft delete a course"""
        course = CourseService.get_course_by_id(course_id, require_active=False)
        if not course:
            return Response(
                {'error': 'Course not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        CourseService.soft_delete_course(course)
        return Response({'message': 'Course deleted successfully'}, status=status.HTTP_204_NO_CONTENT)


class AdminCourseProblemSetView(APIView):
    """Admin endpoint for managing problem sets in a course"""
    permission_classes = [IsAdmin]
    
    def post(self, request, course_id):
        """Add a problem set to a course"""
        course = CourseService.get_course_by_id(course_id, require_active=False)
        if not course:
            return Response(
                {'error': 'Course not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        problem_set_id = request.data.get('problem_set_id')
        order = request.data.get('order', 0)
        is_required = request.data.get('is_required', True)
        
        # Use service layer to add problem set - need to convert from ID to slug
        # This is a limitation in the current implementation - we should ideally use IDs
        try:
            from .repositories.problem_repository import ProblemRepository
            problem_set = ProblemRepository.get_by_id(problem_set_id)
            if not problem_set:
                return Response(
                    {'error': 'Problem set not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            result = CourseService.add_problem_set_to_course(
                course, problem_set.slug, order, is_required
            )
            
            if not result['success']:
                return Response(
                    {'error': result['error']}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            course_ps = result['course_problem_set']
            problem_set = result['problem_set']
            
            return Response({
                'id': course_ps.id,
                'problem_set': ProblemSetListSerializer(problem_set).data,
                'order': course_ps.order,
                'is_required': course_ps.is_required
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error adding problem set to course: {str(e)}")
            return Response(
                {'error': 'Failed to add problem set to course'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, course_id, ps_id):
        """Remove a problem set from a course"""
        course = CourseService.get_course_by_id(course_id, require_active=False)
        if not course:
            return Response(
                {'error': 'Course not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Convert ps_id to slug
        try:
            from .repositories.problem_repository import ProblemRepository
            problem_set = ProblemRepository.get_by_id(ps_id)
            if not problem_set:
                return Response(
                    {'error': 'Problem set not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            result = CourseService.remove_problem_set_from_course(course, problem_set.slug)
            
            if not result['success']:
                return Response(
                    {'error': result['error']}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            logger.error(f"Error removing problem set from course: {str(e)}")
            return Response(
                {'error': 'Failed to remove problem set from course'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Instructor Views
class InstructorCourseListView(APIView):
    """List courses for an instructor"""
    permission_classes = [IsInstructor]
    
    def get(self, request):
        """List instructor's courses"""
        courses = CourseService.get_instructor_courses(request.user)
        serializer = CourseListSerializer(courses, many=True)
        return Response(serializer.data)


class InstructorCourseDetailView(APIView):
    """Get course details for instructor"""
    permission_classes = [IsCourseInstructor]
    
    def get(self, request, course_id):
        """Get course details"""
        course = CourseService.get_course_by_id(course_id, require_active=True)
        if not course:
            return Response(
                {'error': 'Course not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check object-level permission
        self.check_object_permissions(request, course)
        
        serializer = CourseDetailSerializer(course)
        return Response(serializer.data)


class InstructorCourseStudentsView(APIView):
    """View enrolled students for a course"""
    permission_classes = [IsCourseInstructor]
    
    def get(self, request, course_id):
        """List enrolled students"""
        course = CourseService.get_course_by_id(course_id, require_active=True)
        if not course:
            return Response(
                {'error': 'Course not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        self.check_object_permissions(request, course)
        
        enrollments = CourseService.get_instructor_course_students(course)
        serializer = CourseEnrollmentSerializer(enrollments, many=True)
        return Response(serializer.data)


class InstructorCourseProgressView(APIView):
    """View student progress in a course"""
    permission_classes = [IsCourseInstructor]
    
    def get(self, request, course_id):
        """Get all student progress for the course"""
        course = CourseService.get_course_by_id(course_id, require_active=True)
        if not course:
            return Response(
                {'error': 'Course not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        self.check_object_permissions(request, course)
        
        progress_data = CourseService.get_instructor_course_progress(course)
        return Response(progress_data)


class InstructorCourseProblemSetOrderView(APIView):
    """Reorder problem sets in a course"""
    permission_classes = [IsCourseInstructor]
    
    def put(self, request, course_id):
        """Update problem set ordering"""
        course = CourseService.get_course_by_id(course_id, require_active=True)
        if not course:
            return Response(
                {'error': 'Course not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        self.check_object_permissions(request, course)
        
        # Expect data like: [{"problem_set_id": 1, "order": 0}, ...]
        ordering_data = request.data.get('ordering', [])
        
        success = CourseService.reorder_course_problem_sets(course, ordering_data)
        
        if success:
            return Response({'message': 'Problem sets reordered successfully'})
        else:
            return Response(
                {'error': 'Failed to reorder problem sets'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Student Course Views
class StudentEnrolledCoursesView(APIView):
    """List courses a student is enrolled in with full progress data"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get enrolled courses with embedded problem set progress"""
        courses_data = CourseService.get_student_enrolled_courses_with_progress(request.user)
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
        
        result = CourseService.lookup_course_for_enrollment(course_id, request.user)
        
        if not result['success']:
            return Response(
                {'error': result['error']},
                status=status.HTTP_404_NOT_FOUND
            )
        
        course = result['course']
        already_enrolled = result['already_enrolled']
        
        return Response({
            'course': {
                'course_id': course.course_id,
                'name': course.name,
                'description': course.description,
                'instructor': course.instructor.get_full_name() or course.instructor.username,
                'problem_sets_count': course.problem_sets.count(),
                'enrollment_open': course.enrollment_open,
            },
            'already_enrolled': already_enrolled
        })


class CourseEnrollView(APIView):
    """Enroll in a course"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Enroll user in course"""
        serializer = CourseEnrollSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        course_id = serializer.validated_data['course_id']
        
        result = CourseService.enroll_user_in_course(request.user, course_id)
        
        if not result['success']:
            return Response(
                {'error': result['error']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        course = result['course']
        enrollment = result['enrollment']
        created = result['created']
        
        return Response({
            'success': True,
            'course': CourseDetailSerializer(course).data,
            'enrolled_at': enrollment.enrolled_at
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class StudentCourseDetailView(APIView):
    """Get course details for enrolled students"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id):
        """Get course with problem sets"""
        course = CourseService.get_course_by_id(course_id, require_active=True)
        if not course:
            return Response(
                {'error': 'Course not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check enrollment using service
        if not CourseService.is_user_enrolled(request.user, course_id):
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
        result = CourseService.get_student_course_progress(request.user, course_id)
        
        if not result['success']:
            error_code = status.HTTP_404_NOT_FOUND if 'not found' in result['error'] else status.HTTP_403_FORBIDDEN
            return Response({'error': result['error']}, status=error_code)
        
        return Response(result['progress'])


# New Admin Views for Course Action Buttons

class AdminCourseProblemSetsView(APIView):
    """Admin endpoint for managing problem sets in a course"""
    permission_classes = [IsAdmin]
    
    def get(self, request, course_id):
        """Get all problem sets assigned to a course"""
        course = CourseService.get_course_by_id(course_id, require_active=False)
        if not course:
            return Response(
                {'error': 'Course not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get problem sets with their order and required status
        course_problem_sets = CourseService.get_course_problem_sets(course)
        
        response_data = []
        for cps in course_problem_sets:
            response_data.append({
                'id': cps['course_problem_set_id'],
                'problem_set': {
                    'slug': cps['problem_set']['slug'],
                    'title': cps['problem_set']['title'],
                    'problems_count': cps['problem_set']['problems_count']
                },
                'order': cps['order'],
                'is_required': cps['is_required'],
                'added_at': cps.get('added_at')  # This might not be in the dict
            })
        
        return Response(response_data)
    
    def post(self, request, course_id):
        """Add a problem set to a course"""
        course = CourseService.get_course_by_id(course_id, require_active=False)
        if not course:
            return Response(
                {'error': 'Course not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        problem_set_slug = request.data.get('problem_set_slug')
        is_required = request.data.get('is_required', False)
        order = request.data.get('order')
        
        if not problem_set_slug:
            return Response(
                {'error': 'problem_set_slug is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = CourseService.add_problem_set_to_course(
            course, problem_set_slug, order, is_required
        )
        
        if not result['success']:
            error_status = status.HTTP_404_NOT_FOUND if 'not found' in result['error'] else status.HTTP_400_BAD_REQUEST
            return Response({'error': result['error']}, status=error_status)
        
        course_ps = result['course_problem_set']
        problem_set = result['problem_set']
        
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
    
    def put(self, request, course_id, problem_set_slug):
        """Update problem set order or required status in course"""
        course = CourseService.get_course_by_id(course_id, require_active=False)
        if not course:
            return Response(
                {'error': 'Course not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Extract update data
        update_data = {}
        if 'order' in request.data:
            update_data['order'] = request.data['order']
        if 'is_required' in request.data:
            update_data['is_required'] = request.data['is_required']
        
        result = CourseService.update_course_problem_set(course, problem_set_slug, **update_data)
        
        if not result['success']:
            return Response(
                {'error': result['error']},
                status=status.HTTP_404_NOT_FOUND
            )
        
        course_ps = result['course_problem_set']
        
        return Response({
            'id': course_ps.id,
            'order': course_ps.order,
            'is_required': course_ps.is_required
        })
    
    def delete(self, request, course_id, problem_set_slug):
        """Remove a problem set from a course"""
        course = CourseService.get_course_by_id(course_id, require_active=False)
        if not course:
            return Response(
                {'error': 'Course not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        result = CourseService.remove_problem_set_from_course(course, problem_set_slug)
        
        if not result['success']:
            return Response(
                {'error': result['error']},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminAvailableProblemSetsView(APIView):
    """Get problem sets not assigned to a specific course"""
    permission_classes = [IsAdmin]
    
    def get(self, request):
        """List problem sets available to add to a course"""
        exclude_course_id = request.query_params.get('exclude_course')
        
        available_problem_sets = CourseService.get_available_problem_sets(exclude_course_id)
        
        response_data = []
        for ps in available_problem_sets:
            response_data.append({
                'slug': ps['slug'],
                'title': ps['title'],
                'problems_count': ps['problems_count'],
                'description': ps['description']
            })
        
        return Response(response_data)


class AdminCourseStudentsView(APIView):
    """Admin endpoint for managing students in a course"""
    permission_classes = [IsAdmin]
    
    def get(self, request, course_id):
        """Get all students enrolled in a course with progress info"""
        course = CourseService.get_course_by_id(course_id, require_active=False)
        if not course:
            return Response(
                {'error': 'Course not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        students_data = CourseService.get_course_students_with_progress(course)
        return Response(students_data)
    
    def delete(self, request, course_id, user_id):
        """Remove a student from a course"""
        course = CourseService.get_course_by_id(course_id, require_active=False)
        if not course:
            return Response(
                {'error': 'Course not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        result = CourseService.remove_student_from_course(course, user_id)
        
        if not result['success']:
            error_status = status.HTTP_404_NOT_FOUND if 'not found' in result['error'] else status.HTTP_400_BAD_REQUEST
            return Response({'error': result['error']}, status=error_status)
        
        return Response(
            {'message': result['message']},
            status=status.HTTP_204_NO_CONTENT
        )