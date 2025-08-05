"""
Tests for user progress tracking including automatic creation, 
best score tracking, and course isolation.
"""
import pytest
from datetime import timedelta
from django.test import TestCase
from django.db import transaction
from unittest.mock import patch

from tests.factories import (
    ProblemFactory, ProblemSetFactory, CourseFactory,
    UserFactory, CourseEnrollmentFactory, UserProgressFactory,
    SubmissionFactory
)
from tests.helpers import ProgressAssertions
from tests.mocks import MockCodeExecutionService
from purplex.problems_app.models import UserProgress
from purplex.submissions_app.models import PromptSubmission


@pytest.mark.django_db
class TestUserProgressCreation(TestCase):
    """Test automatic UserProgress creation and updates."""
    
    def setUp(self):
        self.user = UserFactory.create()
        self.problem = ProblemFactory.create()
        self.problem_set = ProblemSetFactory.create(problems=[self.problem])
        
    def test_progress_created_on_first_submission(self):
        """Test that UserProgress is automatically created on first submission."""
        # Verify no progress exists
        self.assertFalse(
            UserProgress.objects.filter(
                user=self.user,
                problem=self.problem,
                problem_set=self.problem_set
            ).exists()
        )
        
        # Create a submission
        submission = SubmissionFactory.create(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            score=80
        )
        
        # Progress should now exist
        progress = UserProgress.objects.get(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            course=None
        )
        
        ProgressAssertions.assert_progress_updated(progress, {
            'attempts': 1,
            'best_score': 80,
            'status': 'in_progress',  # Not completed (score < 100)
            'is_completed': False
        })
        
    def test_progress_updated_on_subsequent_submissions(self):
        """Test that progress is updated correctly on multiple submissions."""
        # Create initial progress
        progress = UserProgressFactory.create(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            attempts=2,
            best_score=60
        )
        
        # Make a better submission
        submission = SubmissionFactory.create(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            score=85
        )
        
        # Refresh progress
        progress.refresh_from_db()
        
        ProgressAssertions.assert_progress_updated(progress, {
            'attempts': 3,  # Incremented
            'best_score': 85,  # Updated to higher score
            'status': 'in_progress'
        })
        
    def test_progress_completion_status(self):
        """Test that progress status updates to completed when score reaches 100."""
        progress = UserProgressFactory.create(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            attempts=5,
            best_score=90,
            status='in_progress'
        )
        
        # Make a perfect submission
        submission = SubmissionFactory.create(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            score=100
        )
        
        progress.refresh_from_db()
        
        ProgressAssertions.assert_progress_updated(progress, {
            'attempts': 6,
            'best_score': 100,
            'status': 'completed',
            'is_completed': True
        })
        
        # Verify completion time was set
        self.assertIsNotNone(progress.last_submission_at)
        
    def test_time_tracking(self):
        """Test that time spent is tracked correctly."""
        # Create submission with time spent
        submission = SubmissionFactory.create(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            score=75
        )
        submission.time_spent = timedelta(minutes=10)
        submission.save()
        
        progress = UserProgress.objects.get(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set
        )
        
        # Should have accumulated time
        self.assertEqual(progress.total_time_spent, timedelta(minutes=10))
        
        # Add another submission with time
        submission2 = SubmissionFactory.create(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            score=85
        )
        submission2.time_spent = timedelta(minutes=5)
        submission2.save()
        
        progress.refresh_from_db()
        self.assertEqual(progress.total_time_spent, timedelta(minutes=15))


@pytest.mark.django_db
class TestBestScoreTracking(TestCase):
    """Test best score tracking logic."""
    
    def setUp(self):
        self.user = UserFactory.create()
        self.problem = ProblemFactory.create()
        self.problem_set = ProblemSetFactory.create(problems=[self.problem])
        
    def test_best_score_never_decreases(self):
        """Test that best score is maintained even with lower subsequent scores."""
        # Create progress with high score
        progress = UserProgressFactory.create(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            attempts=1,
            best_score=90
        )
        
        # Submit a lower score
        submission = SubmissionFactory.create(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            score=70  # Lower than best
        )
        
        progress.refresh_from_db()
        
        # Best score should remain 90
        self.assertEqual(progress.best_score, 90)
        # But attempts should increase
        self.assertEqual(progress.attempts, 2)
        
    def test_best_score_updates_on_improvement(self):
        """Test that best score updates when a better score is achieved."""
        progress = UserProgressFactory.create(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            attempts=3,
            best_score=75
        )
        
        # Submit higher scores progressively
        scores = [80, 85, 95]
        for i, score in enumerate(scores):
            submission = SubmissionFactory.create(
                user=self.user,
                problem=self.problem,
                problem_set=self.problem_set,
                score=score
            )
            
            progress.refresh_from_db()
            self.assertEqual(progress.best_score, score)
            self.assertEqual(progress.attempts, 4 + i)
            
    def test_zero_score_handling(self):
        """Test that zero scores are properly recorded."""
        # Submit a zero score (all tests failed)
        submission = SubmissionFactory.create(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            score=0
        )
        
        progress = UserProgress.objects.get(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set
        )
        
        self.assertEqual(progress.best_score, 0)
        self.assertEqual(progress.attempts, 1)
        self.assertEqual(progress.status, 'attempted')


@pytest.mark.django_db
class TestCourseIsolation(TestCase):
    """Test that progress is properly isolated by course context."""
    
    def setUp(self):
        self.user = UserFactory.create()
        self.problem = ProblemFactory.create()
        self.problem_set = ProblemSetFactory.create(problems=[self.problem])
        
        # Create two courses with same problem set
        self.course1 = CourseFactory.create(
            course_id='CS101',
            problem_sets=[self.problem_set]
        )
        self.course2 = CourseFactory.create(
            course_id='CS102',
            problem_sets=[self.problem_set]
        )
        
        # Enroll user in both
        CourseEnrollmentFactory.create(user=self.user, course=self.course1)
        CourseEnrollmentFactory.create(user=self.user, course=self.course2)
        
    def test_separate_progress_per_course(self):
        """Test that progress is tracked separately for each course."""
        # Submit in course 1
        submission1 = SubmissionFactory.create(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            course=self.course1,
            score=80
        )
        
        # Submit in course 2
        submission2 = SubmissionFactory.create(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            course=self.course2,
            score=60
        )
        
        # Get progress for each course
        progress1 = UserProgress.objects.get(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            course=self.course1
        )
        
        progress2 = UserProgress.objects.get(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            course=self.course2
        )
        
        # Verify isolation
        ProgressAssertions.assert_progress_isolated_by_course(progress1, progress2)
        
        # Verify independent scores
        self.assertEqual(progress1.best_score, 80)
        self.assertEqual(progress2.best_score, 60)
        
        # Verify independent attempts
        self.assertEqual(progress1.attempts, 1)
        self.assertEqual(progress2.attempts, 1)
        
    def test_progress_without_course_context(self):
        """Test that progress without course context is separate."""
        # Submit without course
        submission_no_course = SubmissionFactory.create(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            course=None,
            score=70
        )
        
        # Submit with course
        submission_with_course = SubmissionFactory.create(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            course=self.course1,
            score=85
        )
        
        # Should have two separate progress records
        progress_no_course = UserProgress.objects.get(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            course=None
        )
        
        progress_with_course = UserProgress.objects.get(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            course=self.course1
        )
        
        self.assertEqual(progress_no_course.best_score, 70)
        self.assertEqual(progress_with_course.best_score, 85)
        
    def test_course_progress_aggregation(self):
        """Test aggregating progress across problems in a course."""
        # Create another problem in the same problem set
        problem2 = ProblemFactory.create(slug='problem-2')
        self.problem_set.problems.add(problem2)
        
        # Submit solutions for both problems in course 1
        SubmissionFactory.create(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            course=self.course1,
            score=100
        )
        
        SubmissionFactory.create(
            user=self.user,
            problem=problem2,
            problem_set=self.problem_set,
            course=self.course1,
            score=80
        )
        
        # Query all progress for user in course 1
        course_progress = UserProgress.objects.filter(
            user=self.user,
            course=self.course1,
            problem_set=self.problem_set
        )
        
        self.assertEqual(course_progress.count(), 2)
        
        # Calculate aggregate statistics
        total_attempts = sum(p.attempts for p in course_progress)
        avg_best_score = sum(p.best_score for p in course_progress) / course_progress.count()
        completed_count = course_progress.filter(is_completed=True).count()
        
        self.assertEqual(total_attempts, 2)
        self.assertEqual(avg_best_score, 90)  # (100 + 80) / 2
        self.assertEqual(completed_count, 1)  # Only first problem completed


@pytest.mark.django_db
class TestProgressEdgeCases(TestCase):
    """Test edge cases and error conditions in progress tracking."""
    
    def setUp(self):
        self.user = UserFactory.create()
        self.problem = ProblemFactory.create()
        self.problem_set = ProblemSetFactory.create(problems=[self.problem])
        
    def test_concurrent_submission_handling(self):
        """Test that concurrent submissions don't cause race conditions."""
        # This would require more sophisticated testing with threading
        # For now, test that the unique constraint works
        
        # Create initial progress
        progress = UserProgressFactory.create(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            course=None
        )
        
        # Try to create duplicate - should update existing
        progress2, created = UserProgress.objects.update_or_create(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            course=None,
            defaults={'attempts': 5}
        )
        
        self.assertFalse(created)  # Should not create new
        self.assertEqual(progress.id, progress2.id)  # Same record
        self.assertEqual(progress2.attempts, 5)  # Updated
        
    def test_progress_deletion_protection(self):
        """Test that progress records are preserved even if submissions are deleted."""
        # Create submission and verify progress created
        submission = SubmissionFactory.create(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            score=90
        )
        
        progress = UserProgress.objects.get(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set
        )
        
        progress_id = progress.id
        
        # Delete the submission
        submission.delete()
        
        # Progress should still exist
        progress_still_exists = UserProgress.objects.filter(id=progress_id).exists()
        self.assertTrue(progress_still_exists)
        
    def test_problem_set_change_handling(self):
        """Test progress when problem is moved between problem sets."""
        # Create progress for problem in original set
        progress1 = UserProgressFactory.create(
            user=self.user,
            problem=self.problem,
            problem_set=self.problem_set,
            attempts=5,
            best_score=80
        )
        
        # Create new problem set and add same problem
        new_problem_set = ProblemSetFactory.create(
            slug='new-set',
            problems=[self.problem]
        )
        
        # Submit to same problem in new set
        submission = SubmissionFactory.create(
            user=self.user,
            problem=self.problem,
            problem_set=new_problem_set,
            score=90
        )
        
        # Should have separate progress for each problem set
        progress2 = UserProgress.objects.get(
            user=self.user,
            problem=self.problem,
            problem_set=new_problem_set
        )
        
        self.assertNotEqual(progress1.id, progress2.id)
        self.assertEqual(progress1.problem_set, self.problem_set)
        self.assertEqual(progress2.problem_set, new_problem_set)
        
        # Original progress unchanged
        progress1.refresh_from_db()
        self.assertEqual(progress1.attempts, 5)
        self.assertEqual(progress1.best_score, 80)