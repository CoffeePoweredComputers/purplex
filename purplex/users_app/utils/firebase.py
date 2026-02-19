"""
Firebase service accessor.

Returns the appropriate Firebase auth client based on the environment:
- Development: MockFirebaseAuth (local, no Firebase infra needed)
- Production: firebase_admin.auth (real Firebase Admin SDK)

This mirrors the pattern in AuthenticationService._initialize_firebase()
but is available as a standalone utility for services that need Firebase
access outside the auth flow (e.g., account deletion).
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)

_firebase_service = None


def get_firebase_service():
    """
    Return the Firebase auth client (mock or real).

    Uses settings.USE_MOCK_FIREBASE to decide. The result is cached
    after the first call.
    """
    global _firebase_service
    if _firebase_service is not None:
        return _firebase_service

    if getattr(settings, "USE_MOCK_FIREBASE", False):
        from purplex.users_app.mock_firebase import MockFirebaseAuth

        _firebase_service = MockFirebaseAuth
    else:
        try:
            from firebase_admin import auth

            _firebase_service = auth
        except ImportError:
            logger.error(
                "firebase-admin is not installed. "
                "Install it for production use or enable USE_MOCK_FIREBASE."
            )
            raise

    return _firebase_service
