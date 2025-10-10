#!/usr/bin/env python3
"""
Generate valid Mock Firebase tokens for k6 load testing.

This script creates pre-computed authentication tokens that k6 can use
for load testing without needing to implement token generation in JavaScript.

Usage:
    python tests/load/generate_test_tokens.py
"""
import sys
import os
import time
import base64
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Set environment to development
os.environ['PURPLEX_ENV'] = 'development'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'purplex.settings')

import django
django.setup()

from purplex.users_app.mock_firebase import MockFirebaseAuth


def generate_long_lived_token(email: str) -> str:
    """
    Generate a long-lived Mock Firebase token for testing.

    Args:
        email: User email address

    Returns:
        Mock Firebase token string in the format: MOCK.<base64_payload>.development
    """
    # Find user data
    user_data = MockFirebaseAuth.TEST_USERS.get(email)
    if not user_data:
        # Default user data for unknown emails
        uid = f'mock-uid-{email.replace("@", "-").replace(".", "-")}'
        name = email.split('@')[0]
    else:
        uid = user_data['uid']
        name = user_data['name']

    # Create payload with long expiry (10 years for testing)
    now = int(time.time())
    expiry = now + (10 * 365 * 24 * 3600)  # 10 years

    payload = {
        'email': email,
        'uid': uid,
        'name': name,
        'iat': now,
        'exp': expiry,
        'email_verified': True
    }

    # Encode payload as base64
    payload_json = json.dumps(payload)
    payload_b64 = base64.b64encode(payload_json.encode('utf-8')).decode('utf-8')

    # Create token in mock format
    token = f'MOCK.{payload_b64}.development'

    return token


def verify_token(token: str) -> bool:
    """
    Verify that a token can be decoded by MockFirebaseAuth.

    Args:
        token: Token to verify

    Returns:
        True if token is valid
    """
    try:
        decoded = MockFirebaseAuth.verify_id_token(token)
        return decoded is not None
    except Exception as e:
        print(f"Token verification failed: {e}")
        return False


def main():
    """Generate and verify tokens for all test users."""

    print("Generating Mock Firebase tokens for k6 load testing...")
    print("=" * 80)
    print()

    test_users = [
        'student@test.local',
        'student2@test.local',
        'admin@test.local',
        'instructor@test.local',
        'dhsmith2@illinois.edu'
    ]

    tokens = {}

    for email in test_users:
        print(f"Generating token for: {email}")
        token = generate_long_lived_token(email)

        # Verify token works
        if verify_token(token):
            tokens[email] = token
            print(f"  ✓ Token generated and verified")
        else:
            print(f"  ✗ Token verification failed!")
            continue

        print()

    # Output tokens in format ready for k6
    print("=" * 80)
    print("Copy these tokens to tests/load/k6/helpers/auth.js:")
    print("=" * 80)
    print()
    print("const MOCK_TOKENS = {")
    for email, token in tokens.items():
        key = email.replace('@', '_').replace('.', '_')
        print(f"  '{key}': '{token}',")
    print("};")
    print()

    # Also output as environment variable format
    print("=" * 80)
    print("Or export as environment variables:")
    print("=" * 80)
    print()
    for email, token in tokens.items():
        env_var = email.replace('@', '_').replace('.', '_').upper()
        print(f'export K6_TOKEN_{env_var}="{token}"')
    print()

    # Save to file for k6
    output_file = os.path.join(os.path.dirname(__file__), 'k6', 'helpers', 'tokens.json')
    with open(output_file, 'w') as f:
        json.dump(tokens, f, indent=2)

    print(f"✓ Tokens saved to: {output_file}")
    print()
    print("Tokens are valid for 10 years. Regenerate if needed with:")
    print("  python tests/load/generate_test_tokens.py")


if __name__ == '__main__':
    main()