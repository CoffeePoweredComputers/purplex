#!/bin/bash

echo "========================================="
echo "FIREBASE AUTHENTICATION DIAGNOSTIC & FIX"
echo "========================================="

echo -e "\n1. Checking container name..."
CONTAINER_NAME=$(docker ps --format "{{.Names}}" | grep web | head -1)
echo "Container: $CONTAINER_NAME"

echo -e "\n2. Checking Firebase credentials file..."
docker exec $CONTAINER_NAME ls -la /app/firebase-credentials.json 2>&1

echo -e "\n3. Checking Firebase project IDs..."
BACKEND_PROJECT=$(docker exec $CONTAINER_NAME python -c "
import json
try:
    with open('/app/firebase-credentials.json') as f:
        print(json.load(f).get('project_id', 'NOT FOUND'))
except Exception as e:
    print(f'ERROR: {e}')
" 2>&1)
echo "Backend Firebase Project: $BACKEND_PROJECT"
echo "Frontend Firebase Project: purplex-97ff2"

if [ "$BACKEND_PROJECT" != "purplex-97ff2" ]; then
    echo "❌ PROJECT MISMATCH! Backend: $BACKEND_PROJECT, Frontend: purplex-97ff2"
else
    echo "✅ Projects match"
fi

echo -e "\n4. Checking Django settings..."
docker exec $CONTAINER_NAME python -c "
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'purplex.settings'
import django
django.setup()
from django.conf import settings

print('PURPLEX_ENV:', os.environ.get('PURPLEX_ENV', 'not set'))
print('USE_MOCK_FIREBASE:', getattr(settings, 'USE_MOCK_FIREBASE', 'not defined'))
print('FIREBASE_CREDENTIALS_PATH:', os.environ.get('FIREBASE_CREDENTIALS_PATH', 'not set'))
" 2>&1

echo -e "\n5. Checking Firebase initialization..."
docker exec $CONTAINER_NAME python -c "
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'purplex.settings'
import django
django.setup()

from purplex.users_app.services.authentication_service import AuthenticationService
import firebase_admin

print('Firebase app in AuthService:', AuthenticationService._firebase_app is not None)
print('Firebase admin apps:', len(firebase_admin._apps))

if not AuthenticationService._firebase_app:
    print('⚠️  Firebase NOT initialized in AuthenticationService!')
    print('Attempting to initialize...')
    try:
        AuthenticationService._initialize_firebase()
        print('✅ Firebase initialized successfully!')
    except Exception as e:
        print(f'❌ Initialization failed: {e}')
else:
    try:
        app = firebase_admin.get_app()
        print(f'✅ Firebase app active: {app.name}')
    except Exception as e:
        print(f'❌ Error getting app: {e}')
" 2>&1

echo -e "\n6. Testing token validation..."
docker exec $CONTAINER_NAME python -c "
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'purplex.settings'
import django
django.setup()

from purplex.users_app.services.authentication_service import AuthenticationService

# Make sure Firebase is initialized
if not AuthenticationService._firebase_app:
    try:
        AuthenticationService._initialize_firebase()
    except:
        pass

# Test with fake token
try:
    user, data = AuthenticationService.authenticate_token('fake-token')
    print('Unexpected success with fake token!')
except ValueError as e:
    print(f'Expected error with fake token: {str(e)[:100]}')
except Exception as e:
    print(f'Unexpected error type: {type(e).__name__}: {str(e)[:100]}')
" 2>&1

echo -e "\n7. Checking recent authentication errors in logs..."
docker logs $CONTAINER_NAME --tail=20 2>&1 | grep -E "Firebase|firebase|Authentication|403" | tail -5

echo -e "\n8. Checking if USE_MOCK_FIREBASE is set..."
docker exec $CONTAINER_NAME printenv | grep FIREBASE

echo -e "\n========================================="
echo "DIAGNOSIS COMPLETE"
echo "========================================="

echo -e "\nCommon fixes:"
echo "1. If project IDs don't match: You need the correct firebase-credentials.json"
echo "2. If Firebase not initialized: Restart the container"
echo "3. If USE_MOCK_FIREBASE=True: Remove it from .env and restart"