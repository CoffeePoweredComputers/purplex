"""
Unit tests for concurrent authentication to ensure no database locking issues.
"""

import pytest
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.db import connections, transaction

from purplex.users_app.services.authentication_service import AuthenticationService
from purplex.users_app.models import UserProfile
from purplex.users_app.repositories.user_profile_repository import UserProfileRepository


class ConcurrentAuthenticationTest(TransactionTestCase):
    """
    Test concurrent authentication doesn't cause database locking issues.

    Uses TransactionTestCase to properly test database-level concurrency.
    """

    def setUp(self):
        """Set up test environment."""
        # Clear any existing data
        UserProfile.objects.all().delete()
        User.objects.filter(username__startswith='test').delete()

    def tearDown(self):
        """Clean up after tests."""
        # Close all database connections to reset any transaction state
        for conn in connections.all():
            conn.close()

    def test_concurrent_get_or_create_same_user(self):
        """
        Test that concurrent calls to get_or_create_user for the same user
        don't cause database errors or locks.
        """
        firebase_uid = "test-concurrent-uid-123"
        email = "concurrent@example.com"
        display_name = "Concurrent User"

        results = []
        errors = []

        def create_user():
            """Function to run in each thread."""
            try:
                user = AuthenticationService.get_or_create_user(
                    firebase_uid, email, display_name
                )
                results.append(user)
            except Exception as e:
                errors.append(e)

        # Create multiple threads trying to create the same user
        threads = [threading.Thread(target=create_user) for _ in range(10)]

        # Start all threads
        for t in threads:
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join(timeout=5)  # 5-second timeout per thread

        # Assertions
        self.assertEqual(len(errors), 0, f"Should have no errors, got: {errors}")
        self.assertEqual(len(results), 10, "Should have 10 results")

        # All results should be the same user
        user_ids = set(u.id for u in results)
        self.assertEqual(len(user_ids), 1, "All threads should get the same user")

        # Check that only one UserProfile was created
        profile_count = UserProfile.objects.filter(firebase_uid=firebase_uid).count()
        self.assertEqual(profile_count, 1, "Should have exactly one UserProfile")

    def test_concurrent_get_or_create_different_users(self):
        """
        Test that concurrent calls to get_or_create_user for different users
        work without interference.
        """
        num_users = 20
        results = []
        errors = []

        def create_user(index):
            """Function to create a unique user."""
            try:
                user = AuthenticationService.get_or_create_user(
                    f"test-uid-{index}",
                    f"user{index}@example.com",
                    f"User {index}"
                )
                return user
            except Exception as e:
                return e

        # Use ThreadPoolExecutor for better thread management
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(create_user, i): i for i in range(num_users)}

            for future in as_completed(futures):
                result = future.result()
                if isinstance(result, Exception):
                    errors.append(result)
                else:
                    results.append(result)

        # Assertions
        self.assertEqual(len(errors), 0, f"Should have no errors, got: {errors}")
        self.assertEqual(len(results), num_users, f"Should create {num_users} users")

        # Check all users are different
        user_ids = set(u.id for u in results)
        self.assertEqual(len(user_ids), num_users, "All users should be unique")

        # Check UserProfiles were created correctly
        profile_count = UserProfile.objects.count()
        self.assertEqual(profile_count, num_users, f"Should have {num_users} UserProfiles")

    def test_no_select_for_update_in_authentication(self):
        """
        Test that the authentication flow doesn't use select_for_update.

        This test inspects the SQL queries to ensure no SELECT FOR UPDATE.
        """
        from django.test.utils import override_settings
        from django.db import connection

        # Enable query logging
        with override_settings(DEBUG=True):
            # Reset queries
            from django.db import reset_queries
            reset_queries()

            # Perform authentication
            user = AuthenticationService.get_or_create_user(
                "test-no-lock-uid",
                "nolock@example.com",
                "No Lock User"
            )

            # Check queries
            queries = [q['sql'] for q in connection.queries]

            # Assert no SELECT FOR UPDATE queries
            for query in queries:
                self.assertNotIn(
                    'FOR UPDATE',
                    query.upper(),
                    f"Found SELECT FOR UPDATE in query: {query}"
                )

    def test_performance_under_load(self):
        """
        Test that authentication remains performant under concurrent load.

        This test measures the time taken for concurrent authentications.
        """
        num_requests = 50
        max_time_per_request = 0.1  # 100ms max per request

        def timed_create_user(index):
            """Create user and return time taken."""
            start = time.time()
            try:
                user = AuthenticationService.get_or_create_user(
                    f"perf-test-uid-{index}",
                    f"perf{index}@example.com",
                    f"Performance User {index}"
                )
                duration = time.time() - start
                return duration, None
            except Exception as e:
                duration = time.time() - start
                return duration, e

        # Run concurrent requests
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(timed_create_user, i) for i in range(num_requests)]

            durations = []
            errors = []

            for future in as_completed(futures):
                duration, error = future.result()
                durations.append(duration)
                if error:
                    errors.append(error)

        # Assertions
        self.assertEqual(len(errors), 0, f"Should have no errors, got: {errors}")

        # Check performance
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        p95_duration = sorted(durations)[int(len(durations) * 0.95)]

        print(f"\nPerformance results:")
        print(f"  Average: {avg_duration:.3f}s")
        print(f"  Maximum: {max_duration:.3f}s")
        print(f"  P95: {p95_duration:.3f}s")

        # P95 should be under our threshold
        self.assertLess(
            p95_duration,
            max_time_per_request,
            f"P95 latency {p95_duration:.3f}s exceeds threshold {max_time_per_request}s"
        )

    def test_get_or_create_handles_integrity_errors(self):
        """
        Test that the new implementation properly handles IntegrityError
        when two threads try to create the same user simultaneously.
        """
        firebase_uid = "integrity-test-uid"

        # Create a barrier to synchronize thread starts
        barrier = threading.Barrier(2)
        results = []
        errors = []

        def create_with_barrier():
            """Create user after waiting at barrier."""
            barrier.wait()  # Synchronize start
            try:
                # Both threads will try to create at nearly the same time
                profile, user = UserProfileRepository.get_or_create_with_user(
                    firebase_uid,
                    "integrity@example.com",
                    "Integrity Test"
                )
                results.append((profile, user))
            except Exception as e:
                errors.append(e)

        # Create two threads that will start simultaneously
        threads = [threading.Thread(target=create_with_barrier) for _ in range(2)]

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=5)

        # Should have no errors - IntegrityError should be handled
        self.assertEqual(len(errors), 0, f"Should handle IntegrityError gracefully, got: {errors}")
        self.assertEqual(len(results), 2, "Both threads should complete successfully")

        # Both should get the same user
        if len(results) == 2:
            user1_id = results[0][1].id
            user2_id = results[1][1].id
            self.assertEqual(user1_id, user2_id, "Both threads should get the same user")


@pytest.mark.django_db(transaction=True)
class TestConcurrentAuthenticationPytest:
    """
    Pytest version of concurrent authentication tests.

    Uses pytest fixtures and marks for better test organization.
    """

    @pytest.mark.performance
    def test_authentication_without_locking(self, db):
        """
        Test that authentication completes quickly without database locks.
        """
        start = time.time()

        # Create a user
        user = AuthenticationService.get_or_create_user(
            "pytest-perf-uid",
            "pytest@example.com",
            "Pytest User"
        )

        duration = time.time() - start

        # Should complete quickly (under 50ms in normal conditions)
        assert duration < 0.05, f"Authentication took {duration:.3f}s, expected < 0.05s"
        assert user is not None
        assert user.username is not None

    @pytest.mark.integration
    def test_repository_get_or_create_with_user(self, db):
        """
        Test the new repository method directly.
        """
        # First call creates
        profile1, user1 = UserProfileRepository.get_or_create_with_user(
            "repo-test-uid",
            "repo@example.com",
            "Repository Test"
        )

        assert profile1.was_created is True
        assert user1 is not None
        assert profile1.user == user1

        # Second call retrieves
        profile2, user2 = UserProfileRepository.get_or_create_with_user(
            "repo-test-uid",
            "repo@example.com",
            "Repository Test"
        )

        assert profile2.was_created is False
        assert profile2.id == profile1.id
        assert user2.id == user1.id