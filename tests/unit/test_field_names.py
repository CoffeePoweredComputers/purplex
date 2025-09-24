"""Tests to validate Django model field names and relationships."""

from django.test import TestCase
from django.contrib.auth.models import User
from purplex.problems_app.models import (
    Problem,
    ProblemSet,
    ProblemSetMembership,
    Course,
    CourseProblemSet,
    CourseEnrollment,
    UserProgress,
    UserProblemSetProgress,
)


class TestFieldNames(TestCase):
    """Test that Django field names match expected patterns."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        self.instructor = User.objects.create_user(
            username='instructor',
            email='instructor@example.com'
        )
    
    def test_problemset_reverse_relations(self):
        """Verify ProblemSet reverse relation names."""
        problem_set = ProblemSet.objects.create(
            title="Test Problem Set",
            slug="test-problem-set"
        )
        
        # Test through relationship - SHOULD have _set for object access
        self.assertTrue(
            hasattr(problem_set, 'problemsetmembership_set'),
            "ProblemSet should have 'problemsetmembership_set' accessor for object access"
        )
        self.assertFalse(
            hasattr(problem_set, 'problemsetmembership'),
            "ProblemSet should NOT have 'problemsetmembership' accessor without _set"
        )
        
        # Test other reverse relations
        self.assertTrue(
            hasattr(problem_set, 'courseproblemset_set'),
            "ProblemSet should have 'courseproblemset_set' accessor"
        )
        self.assertTrue(
            hasattr(problem_set, 'userprogress_set'),
            "ProblemSet should have 'userprogress_set' accessor"
        )
    
    def test_course_reverse_relations(self):
        """Verify Course reverse relation names."""
        course = Course.objects.create(
            course_id="TEST101",
            name="Test Course",
            instructor=self.instructor
        )
        
        # Test reverse FK - SHOULD have _set suffix for object access
        self.assertTrue(
            hasattr(course, 'courseproblemset_set'),
            "Course should have 'courseproblemset_set' accessor for object access"
        )
        self.assertFalse(
            hasattr(course, 'courseproblemset'),
            "Course should NOT have 'courseproblemset' accessor without _set"
        )
        
        # Test other reverse relations
        self.assertTrue(
            hasattr(course, 'enrollments'),
            "Course should have 'enrollments' accessor (custom related_name)"
        )
    
    def test_problem_reverse_relations(self):
        """Verify Problem reverse relation names."""
        problem = Problem.objects.create(
            slug="test-problem",
            title="Test Problem",
            description="Test description"
        )
        
        # Test reverse relations
        self.assertTrue(
            hasattr(problem, 'problemsetmembership_set'),
            "Problem should have 'problemsetmembership_set' accessor"
        )
        self.assertTrue(
            hasattr(problem, 'userprogress_set'),
            "Problem should have 'userprogress_set' accessor"
        )
        self.assertTrue(
            hasattr(problem, 'test_cases'),
            "Problem should have 'test_cases' accessor (custom related_name)"
        )
    
    def test_user_custom_related_names(self):
        """Verify User model custom related_names."""
        # Test custom related_names
        self.assertTrue(
            hasattr(self.instructor, 'instructed_courses'),
            "User should have 'instructed_courses' accessor from Course.instructor"
        )
        self.assertTrue(
            hasattr(self.user, 'course_enrollments'),
            "User should have 'course_enrollments' accessor from CourseEnrollment.user"
        )
        
        # These should use default _set suffix
        self.assertTrue(
            hasattr(self.user, 'userprogress_set'),
            "User should have 'userprogress_set' accessor"
        )
    
    def test_through_model_queries(self):
        """Test that queries using through models work correctly."""
        problem_set = ProblemSet.objects.create(
            title="Query Test Set",
            slug="query-test-set"
        )
        problem = Problem.objects.create(
            slug="query-test-problem",
            title="Query Test Problem"
        )
        
        # Create membership
        ProblemSetMembership.objects.create(
            problem_set=problem_set,
            problem=problem,
            order=1
        )
        
        # Test query with correct field name
        from django.db.models import Count
        
        # This should work (using problemsetmembership, not problemsetmembership_set)
        annotated = ProblemSet.objects.annotate(
            problem_count=Count('problemsetmembership')
        ).first()
        
        self.assertEqual(
            annotated.problem_count, 1,
            "Count with 'problemsetmembership' should work"
        )
        
        # Test prefetch
        prefetched = ProblemSet.objects.prefetch_related(
            'problemsetmembership_set__problem'
        ).first()
        
        # This should not raise an error
        memberships = list(prefetched.problemsetmembership_set.all())
        self.assertEqual(len(memberships), 1)
    
    def test_course_problemset_queries(self):
        """Test queries with CourseProblemSet."""
        course = Course.objects.create(
            course_id="QUERY101",
            name="Query Course",
            instructor=self.instructor
        )
        problem_set = ProblemSet.objects.create(
            title="Course Query Set",
            slug="course-query-set"
        )
        
        # Create course problem set
        CourseProblemSet.objects.create(
            course=course,
            problem_set=problem_set,
            order=1
        )
        
        # Test with correct _set suffix
        from django.db.models import Count
        
        annotated = Course.objects.annotate(
            ps_count=Count('courseproblemset')
        ).first()
        
        self.assertEqual(
            annotated.ps_count, 1,
            "Count with 'courseproblemset' should work"
        )
        
        # Test prefetch
        prefetched = Course.objects.prefetch_related(
            'courseproblemset_set__problem_set'
        ).first()
        
        # This should work
        course_problem_sets = list(prefetched.courseproblemset_set.all())
        self.assertEqual(len(course_problem_sets), 1)