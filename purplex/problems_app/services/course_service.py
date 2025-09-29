"""Service for managing course-related business logic."""

import logging
from typing import Dict, Any, Optional, Tuple, List, TYPE_CHECKING
from rest_framework import status

from ..repositories import CourseRepository
from ..repositories.problem_repository import ProblemRepository
from ..repositories.progress_repository import ProgressRepository
from ..repositories.course_problem_set_repository import CourseProblemSetRepository
from ..repositories.problem_set_repository import ProblemSetRepository
from users_app.repositories import UserRepository

if TYPE_CHECKING:
    from ..models import CourseProblemSet

logger = logging.getLogger(__name__)


class CourseService:
    """Handle all course-related business logic."""
    
    @staticmethod
    def validate_course_enrollment(user, course_id: str) -> Dict[str, Any]:
        """
        Validate user enrollment in a course.
        
        Args:
            user: Django User instance
            course_id: Course identifier string
            
        Returns:
            Dict with 'success', 'course', 'error', 'status_code' keys
            
        Raises:
            ValueError: If course_id is invalid
        """
        if not course_id:
            raise ValueError("course_id cannot be empty")
            
        course = CourseRepository.get_active_course(course_id)
        
        if not course:
            return {
                'success': False,
                'error': 'Course not found',
                'status_code': status.HTTP_404_NOT_FOUND,
                'course': None
            }
        
        # Check enrollment using repository
        if not CourseRepository.user_is_enrolled(user, course):
            return {
                'success': False,
                'error': 'You are not enrolled in this course',
                'status_code': status.HTTP_403_FORBIDDEN,
                'course': None
            }
        
        return {
            'success': True,
            'course': course,
            'error': None,
            'status_code': status.HTTP_200_OK
        }
    
    @staticmethod
    def get_course_by_id(course_id: str, require_active: bool = True) -> Optional[Any]:
        """
        Get course by ID with validation.
        
        Args:
            course_id: Course identifier (string, e.g., "CS101-FALL2024")
            require_active: Whether to require is_active=True
            
        Returns:
            Course instance or None if not found
        """
        if require_active:
            return CourseRepository.get_active_course(course_id)
        else:
            return CourseRepository.get_course_by_id(course_id)
    
    @staticmethod
    def get_course_by_pk(pk: int) -> Optional[Any]:
        """
        Get course by primary key (integer ID).
        
        Args:
            pk: Primary key (integer ID)
            
        Returns:
            Course instance or None if not found
        """
        return CourseRepository.get_course_by_pk(pk)
    
    @staticmethod
    def authorize_user_course_access(user, course_id: str) -> Tuple[bool, Optional[Any], Optional[str]]:
        """
        Authorize user access to a course.
        
        Args:
            user: Django User instance
            course_id: Course identifier
            
        Returns:
            Tuple of (is_authorized, course_or_none, error_message_or_none)
        """
        course = CourseService.get_course_by_id(course_id, require_active=True)
        
        if not course:
            return False, None, 'Course not found'
        
        # Check if user is enrolled using repository
        if not CourseRepository.user_is_enrolled(user, course):
            return False, None, 'You are not enrolled in this course'
        
        return True, course, None
    
    @staticmethod
    def get_user_courses(user) -> List[Dict[str, Any]]:
        """
        Get all courses a user is enrolled in.
        
        Args:
            user: Django User instance
            
        Returns:
            List of dicts with course data
        """
        return CourseRepository.get_user_enrolled_courses_with_data(user.id)
    
    @staticmethod
    def is_user_enrolled(user, course_id: str) -> bool:
        """
        Check if a user is enrolled in a specific course.
        
        Args:
            user: Django User instance
            course_id: Course identifier
            
        Returns:
            Boolean indicating enrollment status
        """
        course = CourseService.get_course_by_id(course_id, require_active=True)
        if not course:
            return False
        
        return CourseRepository.user_is_enrolled(user, course)
    
    # Admin Course Management Methods
    
    @staticmethod
    def get_all_courses_with_stats() -> List[Dict[str, Any]]:
        """
        Get all courses with problem sets and enrollment counts for admin view.
        
        Returns:
            List of dicts with course statistics
        """
        return CourseRepository.get_all_courses_with_stats()
    
    @staticmethod
    def get_active_courses_with_stats() -> List[Dict[str, Any]]:
        """Get only active courses with statistics.
        
        Returns:
            List of dicts with active course statistics
        """
        return CourseRepository.get_active_courses_with_stats()
    
    @staticmethod
    def create_course(instructor: 'User', **course_data) -> Any:
        """
        Create a new course.
        
        Args:
            instructor: User who will be the instructor
            **course_data: Course field data
            
        Returns:
            Created Course instance
        """
        return CourseRepository.create(instructor=instructor, **course_data)
    
    @staticmethod
    def update_course(course, **update_data) -> Any:
        """
        Update course details.
        
        Args:
            course: Course instance to update
            **update_data: Fields to update
            
        Returns:
            Updated Course instance
        """
        for field, value in update_data.items():
            setattr(course, field, value)
        course.save()
        return course
    
    @staticmethod
    def soft_delete_course(course) -> bool:
        """
        Soft delete a course.
        
        Args:
            course: Course instance to delete
            
        Returns:
            True if successful
        """
        course.soft_delete()
        return True
    
    # Instructor Course Management Methods
    
    @staticmethod
    def get_instructor_courses(instructor) -> List[Dict[str, Any]]:
        """Get all courses for an instructor with statistics.
        
        Args:
            instructor: User instance who is the instructor
            
        Returns:
            List of dicts with course statistics
        """
        return CourseRepository.get_instructor_courses_with_stats(instructor.id)
    
    @staticmethod
    def get_instructor_course_students(course) -> List[Dict[str, Any]]:
        """Get all enrolled students for an instructor's course.
        
        Args:
            course: Course instance
            
        Returns:
            List of dicts with enrollment and user data
        """
        return CourseRepository.get_course_enrollments_with_users(course.id)
    
    @staticmethod
    def get_instructor_course_progress(course) -> List[Dict[str, Any]]:
        """
        Get comprehensive progress data for all students in a course.
        
        Args:
            course: Course instance
            
        Returns:
            List of student progress data
        """
        enrollments = CourseRepository.get_course_enrollments_with_users(course.id)
        progress_data = []
        
        for enrollment_data in enrollments:
            user_id = enrollment_data['user']['id']
            user_progress = ProgressRepository.get_user_course_progress_by_id(user_id, course.id)
            
            # Aggregate problem set progress
            problem_set_progress = {}
            for progress in user_progress:
                ps_id = progress['problem_set_id']
                if ps_id not in problem_set_progress:
                    problem_set_progress[ps_id] = {
                        'problem_set': progress['problem_set_title'],
                        'total_problems': progress['total_problems'],
                        'completed_problems': 0,
                        'average_score': 0,
                        'scores': []
                    }
                
                if progress['is_completed']:
                    problem_set_progress[ps_id]['completed_problems'] += 1
                problem_set_progress[ps_id]['scores'].append(progress['best_score'])
            
            # Calculate averages
            # Note: problem_set_progress is a dict, not a QuerySet - dict.values() is fine
            for ps_data in problem_set_progress.values():  # dict method, not ORM
                if ps_data['scores']:
                    ps_data['average_score'] = sum(ps_data['scores']) / len(ps_data['scores'])
                del ps_data['scores']
            
            progress_data.append({
                'user': enrollment_data['user'],
                'problem_sets': list(problem_set_progress.values())  # dict method, not ORM
            })
        
        return progress_data
    
    @staticmethod
    def reorder_course_problem_sets(course, ordering_data: List[Dict[str, Any]]) -> bool:
        """
        Update problem set ordering for a course.
        
        Args:
            course: Course instance
            ordering_data: List of {'problem_set_id': int, 'order': int}
            
        Returns:
            True if successful
        """
        # Use repository method for bulk reordering
        return CourseProblemSetRepository.reorder_problem_sets(course, ordering_data)
    
    # Course-Problem Set Management Methods
    
    @staticmethod
    def get_course_problem_sets(course) -> List[Dict[str, Any]]:
        """Get all problem sets for a course with metadata.
        
        Args:
            course: Course instance
            
        Returns:
            List of dicts with problem set data
        """
        return CourseRepository.get_course_problem_sets_with_data(course.id)
    
    @staticmethod
    def add_problem_set_to_course(course, problem_set_slug: str, order: Optional[int] = None, 
                                  is_required: bool = True) -> Dict[str, Any]:
        """
        Add a problem set to a course.
        
        Args:
            course: Course instance
            problem_set_slug: Slug of problem set to add
            order: Order position (auto-assigned if None)
            is_required: Whether problem set is required
            
        Returns:
            Dict with success status and created CourseProblemSet data
        """
        problem_set = ProblemRepository.get_problem_set_by_slug(problem_set_slug)
        if not problem_set:
            return {
                'success': False,
                'error': 'Problem set not found'
            }
        
        # Check if already in course
        if CourseRepository.course_has_problem_set(course, problem_set):
            return {
                'success': False,
                'error': 'Problem set is already in this course'
            }
        
        # Auto-assign order if not provided
        if order is None:
            order = CourseProblemSetRepository.get_next_order(course)
        
        course_ps = CourseProblemSetRepository.add_problem_set_to_course(
            course=course,
            problem_set=problem_set,
            order=order,
            is_required=is_required,
            problem_set_version=problem_set.version
        )
        
        return {
            'success': True,
            'course_problem_set': course_ps,
            'problem_set': problem_set
        }
    
    @staticmethod
    def update_course_problem_set(course, problem_set_slug: str, **update_data) -> Dict[str, Any]:
        """
        Update problem set configuration in a course.
        
        Args:
            course: Course instance
            problem_set_slug: Problem set slug
            **update_data: Fields to update (order, is_required)
            
        Returns:
            Dict with success status and updated data
        """
        # Get the problem set first
        problem_set = ProblemRepository.get_problem_set_by_slug(problem_set_slug)
        if not problem_set:
            return {
                'success': False,
                'error': 'Problem set not found'
            }
        
        course_ps = CourseProblemSetRepository.get_by_course_and_problem_set(course, problem_set)
        if not course_ps:
            return {
                'success': False,
                'error': 'Problem set not found in this course'
            }
        
        try:
            
            for field, value in update_data.items():
                if hasattr(course_ps, field):
                    setattr(course_ps, field, value)
            
            course_ps.save()
            
            return {
                'success': True,
                'course_problem_set': course_ps
            }
            
        except Exception as e:
            logger.error(f"Error updating course problem set: {e}")
            return {
                'success': False,
                'error': 'Failed to update problem set'
            }
    
    @staticmethod
    def remove_problem_set_from_course(course, problem_set_slug: str) -> Dict[str, Any]:
        """
        Remove a problem set from a course.
        
        Args:
            course: Course instance
            problem_set_slug: Problem set slug to remove
            
        Returns:
            Dict with success status
        """
        # Use repository method for deletion
        deleted = CourseProblemSetRepository.delete_by_filter(
            course=course,
            problem_set__slug=problem_set_slug
        )
        deleted_count = deleted[0]
        
        if deleted_count == 0:
            return {
                'success': False,
                'error': 'Problem set not found in this course'
            }
        
        return {'success': True}
    
    @staticmethod
    def get_available_problem_sets(exclude_course_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get problem sets available to add to courses.
        
        Args:
            exclude_course_id: Course ID to exclude problem sets from
            
        Returns:
            List of dicts with available problem sets
        """
        if exclude_course_id:
            return CourseRepository.get_unassigned_problem_sets_for_course(exclude_course_id)
        else:
            # Get all public problem sets
            return ProblemSetRepository.get_all_public_problem_sets()
    
    # Student Course Management Methods
    
    @staticmethod
    def get_student_enrolled_courses_with_progress(user) -> List[Dict[str, Any]]:
        """
        Get all enrolled courses for a student with comprehensive progress data.
        
        Args:
            user: Student user
            
        Returns:
            List of course data with embedded progress
        """
        # Get enrolled courses with problem sets
        enrolled_courses = CourseRepository.get_user_enrolled_courses_with_data(user.id)
        
        courses_data = []
        for course_data in enrolled_courses:
            course_id = course_data['course']['id']
            problem_sets = course_data['problem_sets']
            
            # Get progress for all problem sets in this course
            problem_set_ids = [ps['problem_set_id'] for ps in problem_sets]
            progress_data = ProgressRepository.get_user_problem_set_progress_for_course(
                user.id, problem_set_ids, course_id
            )
            
            # Build progress lookup
            progress_lookup = {p['problem_set_id']: p for p in progress_data}
            
            # Build problem sets with inline progress
            problem_sets_data = []
            completed_sets = 0
            
            for ps in problem_sets:
                ps_id = ps['problem_set_id']
                progress = progress_lookup.get(ps_id, {})
                
                completed = progress.get('completed_problems', 0)
                total = ps['total_problems']
                is_completed = progress.get('is_completed', False)
                
                if is_completed:
                    completed_sets += 1
                
                problem_sets_data.append({
                    'problem_set': {
                        'slug': ps['problem_set_slug'],
                        'title': ps['problem_set_title'],
                        'description': ps['problem_set_description'],
                        'problems_count': total
                    },
                    'progress': {
                        'completed_problems': completed,
                        'total_problems': total,
                        'percentage': int((completed / total * 100) if total > 0 else 0)
                    },
                    'order': ps['order'],
                    'is_required': ps['is_required']
                })
            
            total_sets = len(problem_sets_data)
            
            courses_data.append({
                'course': {
                    'course_id': course_data['course']['course_id'],
                    'name': course_data['course']['name'],
                    'description': course_data['course']['description'],
                    'instructor_name': course_data['course']['instructor_name'],
                    'problem_sets': problem_sets_data
                },
                'enrolled_at': course_data['enrolled_at'],
                'progress': {
                    'completed_sets': completed_sets,
                    'total_sets': total_sets,
                    'percentage': int((completed_sets / total_sets * 100) if total_sets > 0 else 0)
                }
            })
        
        return courses_data
    
    @staticmethod
    def lookup_course_for_enrollment(course_id: str, user) -> Dict[str, Any]:
        """
        Lookup a course for enrollment by a student.
        
        Args:
            course_id: Course identifier
            user: User attempting to enroll
            
        Returns:
            Dict with course info and enrollment status
        """
        course = CourseRepository.get_active_course(course_id)
        
        if not course or not course.enrollment_open:
            return {
                'success': False,
                'error': 'Course not found or enrollment is closed'
            }
        
        # Check if already enrolled
        is_enrolled = CourseRepository.user_is_enrolled(user, course)
        
        return {
            'success': True,
            'course': course,
            'already_enrolled': is_enrolled
        }
    
    @staticmethod
    def enroll_user_in_course(user, course_id: str) -> Dict[str, Any]:
        """
        Enroll a user in a course.
        
        Args:
            user: User to enroll
            course_id: Course identifier
            
        Returns:
            Dict with enrollment result
        """
        course = CourseRepository.get_active_course(course_id)
        
        if not course or not course.enrollment_open:
            return {
                'success': False,
                'error': 'Course not found or enrollment is closed'
            }
        
        # Use repository to handle enrollment
        enrollment, created = CourseRepository.update_or_create_enrollment(
            user, course, {'is_active': True}
        )
        
        if not created and enrollment.is_active:
            return {
                'success': False,
                'error': 'You are already enrolled in this course'
            }
        elif not created:
            # Reactivate enrollment
            enrollment.is_active = True
            enrollment.save()
        
        return {
            'success': True,
            'course': course,
            'enrollment': enrollment,
            'created': created
        }
    
    @staticmethod
    def get_student_course_progress(user, course_id: str) -> Dict[str, Any]:
        """
        Get a student's progress in a specific course.
        
        Args:
            user: Student user
            course_id: Course identifier
            
        Returns:
            Dict with course progress data
        """
        course = CourseRepository.get_active_course(course_id)
        
        if not course:
            return {
                'success': False,
                'error': 'Course not found'
            }
        
        if not CourseRepository.user_is_enrolled(user, course):
            return {
                'success': False,
                'error': 'You are not enrolled in this course'
            }
        
        # Get problem set progress
        problem_set_ids = CourseRepository.get_course_problem_set_ids(course)
        progress_data = ProgressRepository.get_user_problem_set_progress_by_course(
            user, problem_set_ids, course
        )
        
        # Create progress map
        progress_map = {p.problem_set_id: p for p in progress_data}
        
        # Build response with all problem sets
        response_data = []
        for cps in CourseRepository.get_course_problem_sets(course):
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
                    'total_problems': progress.total_problems if progress else ProblemRepository.count_problems_in_set(ps),
                    'percentage': progress.completion_percentage if progress else 0,
                    'is_completed': progress.is_completed if progress else False,
                    'last_activity': progress.last_activity if progress else None
                }
            })
        
        return {
            'success': True,
            'course': course,
            'progress': response_data
        }
    
    # Admin Student Management Methods
    
    @staticmethod
    def get_course_students_with_progress(course) -> List[Dict[str, Any]]:
        """
        Get all students in a course with their progress information.
        
        Args:
            course: Course instance
            
        Returns:
            List of student data with progress
        """
        enrollments = CourseRepository.get_course_enrollments_with_users(course.id)
        problem_sets = CourseRepository.get_course_problem_sets_with_data(course.id)
        total_count = len(problem_sets)
        problem_set_ids = [ps['problem_set']['id'] for ps in problem_sets]
        
        response_data = []
        for enrollment_data in enrollments:
            user_id = enrollment_data['user']['id']
            
            # Get progress summary for this user in this course
            user_progress = ProgressRepository.get_user_problem_set_progress_for_course(
                user_id, problem_set_ids, course.id
            )
            
            completed_count = sum(1 for p in user_progress if p.get('is_completed', False))
            
            response_data.append({
                'user': enrollment_data['user'],
                'enrolled_at': enrollment_data['enrolled_at'],
                'is_active': True,  # Already filtered for active enrollments
                'progress': {
                    'completed_problem_sets': completed_count,
                    'total_problem_sets': total_count,
                    'completion_percentage': int((completed_count / total_count * 100) if total_count > 0 else 0)
                }
            })
        
        return response_data
    
    @staticmethod
    def remove_student_from_course(course, user_id: int) -> Dict[str, Any]:
        """
        Remove a student from a course by deactivating enrollment.
        
        Args:
            course: Course instance
            user_id: ID of user to remove
            
        Returns:
            Dict with success status
        """
        try:
            # Use UserRepository to get user
            user = UserRepository.get_by_id(user_id)
            if not user:
                return {
                    'success': False,
                    'error': 'User not found'
                }
            
            success = CourseRepository.deactivate_enrollment(user, course)
            
            if success:
                return {
                    'success': True,
                    'message': 'Student removed from course successfully'
                }
            else:
                return {
                    'success': False,
                    'error': 'Student not enrolled in this course'
                }
                
        except Exception as e:
            logger.error(f"Error removing student from course: {e}")
            return {
                'success': False,
                'error': 'Failed to remove student from course'
            }