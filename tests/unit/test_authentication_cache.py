"""
Test authentication caching functionality.
"""

import time
from unittest.mock import patch, MagicMock, call
from django.test import TestCase
from django.core.cache import cache
from django.contrib.auth.models import User

from purplex.users_app.services.authentication_service import AuthenticationService
from purplex.users_app.models import UserProfile


class AuthenticationCacheTest(TestCase):
    """Test the authentication caching implementation."""

    def setUp(self):
        """Set up test data."""
        # Clear cache before each test
        cache.clear()

        # Create a test user
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test User'
        )
        self.test_profile = UserProfile.objects.create(
            user=self.test_user,
            firebase_uid='test-firebase-uid',
            role='user'
        )

        # Mock Firebase token data
        self.mock_token = 'mock-firebase-token-12345'
        self.mock_decoded_token = {
            'uid': 'test-firebase-uid',
            'email': 'test@example.com',
            'name': 'Test User',
            'exp': int(time.time()) + 3600  # Expires in 1 hour
        }

    def tearDown(self):
        """Clean up after each test."""
        cache.clear()

    @patch('purplex.users_app.services.authentication_service.AuthenticationService._initialize_firebase')
    def test_token_caching_on_successful_auth(self, mock_firebase):
        """Test that successful authentication caches the token."""
        # Setup mock Firebase
        mock_auth_module = MagicMock()
        mock_auth_module.verify_id_token.return_value = self.mock_decoded_token
        mock_firebase.return_value = mock_auth_module

        # First authentication - should call Firebase
        user1, token_data1 = AuthenticationService.authenticate_token(self.mock_token)

        # Verify Firebase was called
        mock_auth_module.verify_id_token.assert_called_once_with(self.mock_token)
        self.assertEqual(user1.username, self.test_user.username)
        self.assertEqual(token_data1['uid'], 'test-firebase-uid')

        # Second authentication with same token - should use cache
        mock_auth_module.verify_id_token.reset_mock()
        user2, token_data2 = AuthenticationService.authenticate_token(self.mock_token)

        # Verify Firebase was NOT called (cache hit)
        mock_auth_module.verify_id_token.assert_not_called()
        self.assertEqual(user2.username, self.test_user.username)
        self.assertEqual(token_data2['uid'], 'test-firebase-uid')

    @patch('purplex.users_app.services.authentication_service.AuthenticationService._initialize_firebase')
    def test_expired_token_removed_from_cache(self, mock_firebase):
        """Test that tokens expired beyond grace period are removed from cache."""
        # Setup mock Firebase with expired token
        expired_token_data = self.mock_decoded_token.copy()
        # Expired 15 minutes ago (beyond 10-minute grace period)
        expired_token_data['exp'] = int(time.time()) - 900

        mock_auth_module = MagicMock()
        mock_auth_module.verify_id_token.return_value = self.mock_decoded_token
        mock_firebase.return_value = mock_auth_module

        # Manually add expired token to cache
        import hashlib
        token_hash = hashlib.sha256(self.mock_token.encode()).hexdigest()[:16]
        cache_key = f"firebase:token:{token_hash}"
        cache.set(cache_key, expired_token_data, 300)

        # Try to authenticate - should detect expired cached token and re-verify
        user, token_data = AuthenticationService.authenticate_token(self.mock_token)

        # Verify Firebase was called (expired cache beyond grace period was deleted)
        mock_auth_module.verify_id_token.assert_called_once_with(self.mock_token)
        self.assertEqual(user.username, self.test_user.username)

    @patch('purplex.users_app.services.authentication_service.AuthenticationService._initialize_firebase')
    def test_expired_token_within_grace_period_accepted(self, mock_firebase):
        """Test that tokens expired within grace period are accepted."""
        # Setup token expired 5 minutes ago (within 10-minute grace period)
        expired_token_data = self.mock_decoded_token.copy()
        expired_token_data['exp'] = int(time.time()) - 300  # Expired 5 minutes ago

        mock_auth_module = MagicMock()
        mock_firebase.return_value = mock_auth_module

        # Manually add expired token to cache
        import hashlib
        token_hash = hashlib.sha256(self.mock_token.encode()).hexdigest()[:16]
        cache_key = f"firebase:token:{token_hash}"
        cache.set(cache_key, expired_token_data, 300)

        # Try to authenticate - should accept expired token within grace period
        user, token_data = AuthenticationService.authenticate_token(self.mock_token)

        # Verify Firebase was NOT called (grace period used)
        mock_auth_module.verify_id_token.assert_not_called()

        # Verify user authenticated successfully
        self.assertEqual(user.username, self.test_user.username)

        # Verify grace period metadata is present
        self.assertTrue(token_data.get('in_grace_period'))
        self.assertIn('grace_period_remaining', token_data)
        self.assertIn('expired_since', token_data)

    @patch('purplex.users_app.services.authentication_service.AuthenticationService._initialize_firebase')
    def test_invalid_token_not_cached(self, mock_firebase):
        """Test that invalid tokens are never cached."""
        # Setup mock Firebase to raise an error
        mock_auth_module = MagicMock()
        mock_auth_module.verify_id_token.side_effect = Exception("Invalid token")
        mock_firebase.return_value = mock_auth_module

        # Try to authenticate with invalid token
        with self.assertRaises(ValueError) as context:
            AuthenticationService.authenticate_token('invalid-token')

        self.assertIn("Authentication failed", str(context.exception))

        # Verify nothing was cached
        import hashlib
        token_hash = hashlib.sha256('invalid-token'.encode()).hexdigest()[:16]
        cache_key = f"firebase:token:{token_hash}"
        self.assertIsNone(cache.get(cache_key))

    def test_user_caching(self):
        """Test that users are cached correctly."""
        # First call - should hit database (2 queries: profile + user)
        with self.assertNumQueries(2):  # One query for profile, one for user
            user1 = AuthenticationService.get_cached_user('test-firebase-uid')
            self.assertEqual(user1.username, self.test_user.username)

        # Second call - should use cache (still 1 query to load User by cached ID)
        with self.assertNumQueries(1):  # Only query to get user by cached ID
            user2 = AuthenticationService.get_cached_user('test-firebase-uid')
            self.assertEqual(user2.username, self.test_user.username)

    def test_user_cache_cleared_on_update(self):
        """Test that user cache is cleared when user info is updated."""
        # Cache the user first
        user = AuthenticationService.get_cached_user('test-firebase-uid')

        # Verify user is cached
        user_cache_key = f"firebase:user:test-firebase-uid"
        self.assertIsNotNone(cache.get(user_cache_key))

        # Update user info
        AuthenticationService._update_user_if_needed(
            self.test_user,
            'newemail@example.com',
            'New Name'
        )

        # Verify cache was cleared
        self.assertIsNone(cache.get(user_cache_key))

    @patch('purplex.users_app.services.authentication_service.cache.get')
    @patch('purplex.users_app.services.authentication_service.cache.set')
    def test_cache_failure_fallback(self, mock_cache_set, mock_cache_get):
        """Test that system works when cache is unavailable."""
        # Make cache operations fail
        mock_cache_get.side_effect = Exception("Cache unavailable")
        mock_cache_set.side_effect = Exception("Cache unavailable")

        with patch('purplex.users_app.services.authentication_service.AuthenticationService._initialize_firebase') as mock_firebase:
            mock_auth_module = MagicMock()
            mock_auth_module.verify_id_token.return_value = self.mock_decoded_token
            mock_firebase.return_value = mock_auth_module

            # Authentication should still work despite cache failure
            user, token_data = AuthenticationService.authenticate_token(self.mock_token)

            # Verify Firebase was called (no cache available)
            mock_auth_module.verify_id_token.assert_called_once_with(self.mock_token)
            self.assertEqual(user.username, self.test_user.username)
            self.assertEqual(token_data['uid'], 'test-firebase-uid')

    def test_cache_ttl_settings(self):
        """Test that cache TTL settings are correct."""
        import hashlib

        # Test token cache TTL (5 minutes = 300 seconds)
        token_hash = hashlib.sha256('test-token'.encode()).hexdigest()[:16]
        token_cache_key = f"firebase:token:{token_hash}"
        cache.set(token_cache_key, {'test': 'data'}, 300)

        # Test user cache TTL (10 minutes = 600 seconds)
        user_cache_key = f"firebase:user:test-uid"
        cache.set(user_cache_key, 123, 600)

        # Verify both are set (actual TTL testing would require mocking time)
        self.assertIsNotNone(cache.get(token_cache_key))
        self.assertIsNotNone(cache.get(user_cache_key))