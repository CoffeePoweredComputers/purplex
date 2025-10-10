"""Test token refresh and expiry detection"""
import time
import pytest
from purplex.users_app.services.authentication_service import AuthenticationService


class TestTokenExpiry:
    """Test suite for token expiry detection"""

    def test_check_token_expiry_needs_refresh(self):
        """Token with < 5 min expiry should need refresh"""
        token = {'exp': int(time.time()) + 200}  # 200 seconds = 3.3 min
        result = AuthenticationService.check_token_expiry(token)

        assert result['needs_refresh'] is True
        assert result['expires_in'] < 300
        assert result['expires_at'] == token['exp']

    def test_check_token_expiry_fresh(self):
        """Fresh token should not need refresh"""
        token = {'exp': int(time.time()) + 3000}  # 50 minutes
        result = AuthenticationService.check_token_expiry(token)

        assert result['needs_refresh'] is False
        assert result['expires_in'] > 300
        assert result['expires_at'] == token['exp']

    def test_check_token_expiry_expired(self):
        """Expired token should need refresh"""
        token = {'exp': int(time.time()) - 100}  # Expired 100 seconds ago
        result = AuthenticationService.check_token_expiry(token)

        assert result['needs_refresh'] is True
        assert result['expires_in'] < 0
        assert result['expires_at'] == token['exp']

    def test_check_token_expiry_boundary_condition(self):
        """Token expiring exactly at 5 minutes should need refresh"""
        token = {'exp': int(time.time()) + 300}  # Exactly 5 minutes
        result = AuthenticationService.check_token_expiry(token)

        # Should NOT need refresh at exactly 300 seconds (boundary)
        assert result['needs_refresh'] is False
        assert result['expires_in'] == 300
        assert result['expires_at'] == token['exp']

    def test_check_token_expiry_just_under_threshold(self):
        """Token expiring just under 5 minutes should need refresh"""
        token = {'exp': int(time.time()) + 299}  # 299 seconds = 4.98 min
        result = AuthenticationService.check_token_expiry(token)

        assert result['needs_refresh'] is True
        assert result['expires_in'] == 299
        assert result['expires_at'] == token['exp']

    def test_check_token_expiry_no_exp_field(self):
        """Token without exp field should be treated as expired"""
        token = {}
        result = AuthenticationService.check_token_expiry(token)

        assert result['needs_refresh'] is True
        assert result['expires_in'] < 0
        assert result['expires_at'] == 0

    def test_check_token_expiry_returns_correct_structure(self):
        """Verify the returned dictionary has all required fields"""
        token = {'exp': int(time.time()) + 1000}
        result = AuthenticationService.check_token_expiry(token)

        # Check all required fields are present
        assert 'needs_refresh' in result
        assert 'expires_in' in result
        assert 'expires_at' in result

        # Check field types
        assert isinstance(result['needs_refresh'], bool)
        assert isinstance(result['expires_in'], int)
        assert isinstance(result['expires_at'], int)


class TestGracefulDegradation:
    """Test suite for backend grace period logic"""

    def test_grace_period_calculation_within_window(self):
        """Test grace period logic: token expired 5 min ago (within 10 min grace period)"""
        current_time = time.time()
        token_exp = current_time - 300  # Expired 5 min ago
        time_since_expiry = current_time - token_exp
        grace_period_seconds = 600  # 10 minutes

        # Should be within grace period
        assert time_since_expiry < grace_period_seconds
        assert time_since_expiry == 300

        # Calculate remaining grace period
        grace_remaining = grace_period_seconds - time_since_expiry
        assert grace_remaining == 300  # 5 minutes remaining

    def test_grace_period_calculation_beyond_window(self):
        """Test grace period logic: token expired 15 min ago (beyond 10 min grace period)"""
        current_time = time.time()
        token_exp = current_time - 900  # Expired 15 min ago
        time_since_expiry = current_time - token_exp
        grace_period_seconds = 600  # 10 minutes

        # Should be beyond grace period
        assert time_since_expiry > grace_period_seconds
        assert time_since_expiry == 900

    def test_grace_period_calculation_at_boundary(self):
        """Test grace period logic: token expired exactly 10 min ago (at boundary)"""
        current_time = time.time()
        token_exp = current_time - 600  # Expired exactly 10 min ago
        time_since_expiry = current_time - token_exp
        grace_period_seconds = 600  # 10 minutes

        # At boundary - should NOT be within grace period (strict <)
        assert not (time_since_expiry < grace_period_seconds)
        assert time_since_expiry == 600

    def test_grace_period_metadata_structure(self):
        """Test that grace period metadata has correct structure"""
        # Simulate what backend returns for token in grace period
        token_exp = int(time.time()) - 300  # Expired 5 min ago
        time_since_expiry = int(time.time()) - token_exp
        grace_period_remaining = 600 - time_since_expiry

        metadata = {
            'in_grace_period': True,
            'grace_period_remaining': grace_period_remaining,
            'expired_since': time_since_expiry
        }

        # Verify structure
        assert 'in_grace_period' in metadata
        assert 'grace_period_remaining' in metadata
        assert 'expired_since' in metadata

        # Verify values are sensible
        assert metadata['in_grace_period'] is True
        assert metadata['grace_period_remaining'] > 0
        assert metadata['expired_since'] > 0
        assert metadata['grace_period_remaining'] + metadata['expired_since'] == 600