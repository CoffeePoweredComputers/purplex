"""
Mock Firebase service for development environment.
This module provides a Firebase-compatible authentication service that mimics
production behavior without requiring actual Firebase infrastructure.
"""
import jwt
import time
import os
import secrets
from typing import Dict, Optional, List


class MockFirebaseAuth:
    """
    Development mock that behaves like real Firebase.
    
    This class provides the same interface as firebase_admin.auth but
    works entirely locally without requiring Firebase infrastructure.
    """
    
    # Predefined test users for development
    TEST_USERS = {
        'dhsmith2@illinois.edu': {
            'uid': 'mock-uid-dhsmith2',
            'email': 'dhsmith2@illinois.edu',
            'name': 'DH Smith',
            'role': 'admin',
            'is_staff': True,
            'is_superuser': True
        },
        'admin@test.local': {
            'uid': 'mock-uid-admin',
            'email': 'admin@test.local',
            'name': 'Test Admin',
            'role': 'admin',
            'is_staff': True,
            'is_superuser': True
        },
        'instructor@test.local': {
            'uid': 'mock-uid-instructor',
            'email': 'instructor@test.local',
            'name': 'Test Instructor',
            'role': 'instructor',
            'is_staff': True,
            'is_superuser': False
        },
        'student@test.local': {
            'uid': 'mock-uid-student',
            'email': 'student@test.local',
            'name': 'Test Student',
            'role': 'user',
            'is_staff': False,
            'is_superuser': False
        },
        'student2@test.local': {
            'uid': 'mock-uid-student2',
            'email': 'student2@test.local',
            'name': 'Test Student 2',
            'role': 'user',
            'is_staff': False,
            'is_superuser': False
        }
    }
    
    # Mock secret for JWT encoding/decoding in development
    @classmethod
    def get_mock_secret(cls):
        """Get mock JWT secret from environment or generate one."""
        # Never allow mock in production
        if os.environ.get('PURPLEX_ENV') == 'production':
            raise RuntimeError("Mock Firebase cannot be used in production")
        
        # Get from environment or generate random
        mock_secret = os.environ.get('MOCK_JWT_SECRET')
        if not mock_secret:
            # Generate a random secret for this session
            mock_secret = secrets.token_hex(32)
            os.environ['MOCK_JWT_SECRET'] = mock_secret
        
        return mock_secret
    
    @classmethod
    def verify_id_token(cls, token: str, check_revoked: bool = False) -> Dict:
        """
        Verify a mock Firebase ID token.
        
        Args:
            token: The JWT token to verify
            check_revoked: Ignored in mock (for compatibility)
            
        Returns:
            Dict containing the decoded token claims
            
        Raises:
            InvalidIdTokenError: If the token is invalid
            ExpiredIdTokenError: If the token has expired
        """
        # Check if this is a simplified mock token from the frontend
        if token.startswith('MOCK.'):
            try:
                # Format: MOCK.base64(payload).signature
                parts = token.split('.')
                if len(parts) != 3 or parts[2] != 'development':
                    raise InvalidIdTokenError("Invalid mock token format")
                
                # Decode the base64 payload
                import base64
                import json
                payload_str = base64.b64decode(parts[1]).decode('utf-8')
                payload = json.loads(payload_str)
                
                # Check expiration
                import time
                if payload.get('exp', 0) < time.time():
                    raise ExpiredIdTokenError("Mock token has expired")
                
                email = payload.get('email')
                
                # Return user data based on email
                if email in cls.TEST_USERS:
                    user_data = cls.TEST_USERS[email]
                    return {
                        'uid': user_data['uid'],
                        'email': user_data['email'],
                        'name': user_data['name'],
                        'email_verified': True,
                        'iat': payload.get('iat'),
                        'exp': payload.get('exp')
                    }
                
                # For any other email in development, create a student account
                return {
                    'uid': payload.get('uid', f'mock-uid-{email.replace("@", "-").replace(".", "-")}'),
                    'email': email,
                    'name': payload.get('name', email.split('@')[0] if email else 'User'),
                    'email_verified': True,
                    'iat': payload.get('iat'),
                    'exp': payload.get('exp')
                }
                
            except Exception as e:
                raise InvalidIdTokenError(f"Invalid mock token: {str(e)}")
        
        # Fall back to JWT decoding for properly signed tokens
        try:
            # Decode the mock token
            payload = jwt.decode(
                token, 
                cls.get_mock_secret(), 
                algorithms=['HS256'],
                options={"verify_exp": True}
            )
            
            email = payload.get('email')
            
            # Return user data based on email
            if email in cls.TEST_USERS:
                user_data = cls.TEST_USERS[email]
                return {
                    'uid': user_data['uid'],
                    'email': user_data['email'],
                    'name': user_data['name'],
                    'email_verified': True,
                    'iat': payload.get('iat'),
                    'exp': payload.get('exp')
                }
            
            # For any other email in development, create a student account
            return {
                'uid': f'mock-uid-{email.replace("@", "-").replace(".", "-")}',
                'email': email,
                'name': email.split('@')[0],
                'email_verified': True,
                'iat': payload.get('iat'),
                'exp': payload.get('exp')
            }
            
        except jwt.ExpiredSignatureError:
            raise ExpiredIdTokenError("Mock token has expired")
        except jwt.InvalidTokenError as e:
            raise InvalidIdTokenError(f"Invalid mock token: {str(e)}")
    
    @classmethod
    def create_custom_token(cls, uid: str, developer_claims: Optional[Dict] = None) -> bytes:
        """
        Create a custom token for the given user.
        
        Args:
            uid: The user's UID
            developer_claims: Optional custom claims to include
            
        Returns:
            The encoded JWT token as bytes
        """
        # Find user by UID
        email = None
        name = None
        for test_email, test_data in cls.TEST_USERS.items():
            if test_data['uid'] == uid:
                email = test_email
                name = test_data['name']
                break
        
        if not email:
            # Default for unknown UIDs
            email = f"{uid}@test.local"
            name = uid
        
        payload = {
            'uid': uid,
            'email': email,
            'name': name,
            'iat': int(time.time()),
            'exp': int(time.time()) + 3600,  # 1 hour expiry
            'iss': 'mock-firebase',
            'aud': 'mock-firebase-project'
        }
        
        if developer_claims:
            payload.update(developer_claims)
        
        token = jwt.encode(payload, cls.get_mock_secret(), algorithm='HS256')
        return token.encode() if isinstance(token, str) else token
    
    @classmethod
    def create_user(cls, email: str, password: str = None, display_name: str = None) -> 'MockUserRecord':
        """
        Create a new user (mock implementation).
        
        Args:
            email: User's email address
            password: User's password (ignored in mock)
            display_name: User's display name
            
        Returns:
            MockUserRecord object
        """
        uid = f'mock-uid-{email.replace("@", "-").replace(".", "-")}'
        return MockUserRecord(
            uid=uid,
            email=email,
            display_name=display_name or email.split('@')[0]
        )
    
    @classmethod
    def get_user(cls, uid: str) -> 'MockUserRecord':
        """
        Get a user by UID (mock implementation).
        
        Args:
            uid: The user's UID
            
        Returns:
            MockUserRecord object
            
        Raises:
            UserNotFoundError: If user doesn't exist
        """
        # Check test users
        for email, data in cls.TEST_USERS.items():
            if data['uid'] == uid:
                return MockUserRecord(
                    uid=uid,
                    email=email,
                    display_name=data['name']
                )
        
        # For development, allow any UID
        return MockUserRecord(
            uid=uid,
            email=f"{uid}@test.local",
            display_name=uid
        )
    
    @classmethod
    def get_user_by_email(cls, email: str) -> 'MockUserRecord':
        """
        Get a user by email (mock implementation).
        
        Args:
            email: The user's email
            
        Returns:
            MockUserRecord object
        """
        if email in cls.TEST_USERS:
            data = cls.TEST_USERS[email]
            return MockUserRecord(
                uid=data['uid'],
                email=email,
                display_name=data['name']
            )
        
        # For development, create user on the fly
        return MockUserRecord(
            uid=f'mock-uid-{email.replace("@", "-").replace(".", "-")}',
            email=email,
            display_name=email.split('@')[0]
        )
    
    @classmethod
    def delete_user(cls, uid: str) -> None:
        """
        Delete a user (mock implementation - does nothing).
        
        Args:
            uid: The user's UID
        """
        pass  # No-op in mock
    
    @classmethod
    def list_users(cls, page_token: Optional[str] = None, max_results: int = 1000) -> 'MockListUsersPage':
        """
        List users (mock implementation).
        
        Args:
            page_token: Token for pagination (ignored in mock)
            max_results: Maximum number of results
            
        Returns:
            MockListUsersPage object
        """
        users = []
        for email, data in cls.TEST_USERS.items():
            users.append(MockUserRecord(
                uid=data['uid'],
                email=email,
                display_name=data['name']
            ))
        
        return MockListUsersPage(users=users[:max_results])


class MockUserRecord:
    """Mock implementation of Firebase UserRecord"""
    
    def __init__(self, uid: str, email: str, display_name: str = None):
        self.uid = uid
        self.email = email
        self.display_name = display_name or email.split('@')[0]
        self.email_verified = True  # Always verified in mock
        self.disabled = False
        self.provider_data = []
        self.custom_claims = {}
        self.tokens_valid_after_timestamp = int(time.time())


class MockListUsersPage:
    """Mock implementation of Firebase ListUsersPage"""
    
    def __init__(self, users: List[MockUserRecord], next_page_token: Optional[str] = None):
        self.users = users
        self.next_page_token = next_page_token
    
    def iterate_all(self):
        """Iterate through all users"""
        return iter(self.users)


class InvalidIdTokenError(Exception):
    """Raised when an ID token is invalid"""
    pass


class ExpiredIdTokenError(Exception):
    """Raised when an ID token has expired"""
    pass


class UserNotFoundError(Exception):
    """Raised when a user is not found"""
    pass


# Convenience function for creating test tokens
def create_test_token(email: str) -> str:
    """
    Create a test token for the given email.
    
    This is a convenience function for testing.
    
    Args:
        email: The user's email address
        
    Returns:
        A valid mock Firebase token
    """
    if email in MockFirebaseAuth.TEST_USERS:
        uid = MockFirebaseAuth.TEST_USERS[email]['uid']
        name = MockFirebaseAuth.TEST_USERS[email]['name']
    else:
        uid = f'mock-uid-{email.replace("@", "-").replace(".", "-")}'
        name = email.split('@')[0]
    
    payload = {
        'uid': uid,
        'email': email,
        'name': name,
        'iat': int(time.time()),
        'exp': int(time.time()) + 3600,  # 1 hour expiry
        'email_verified': True
    }
    
    return jwt.encode(payload, MockFirebaseAuth.MOCK_SECRET, algorithm='HS256')