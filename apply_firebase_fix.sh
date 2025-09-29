#!/bin/bash

echo "========================================="
echo "APPLYING FIREBASE AUTHENTICATION FIX"
echo "========================================="

# Get container name
CONTAINER_NAME=$(docker ps --format "{{.Names}}" | grep web | head -1)

echo -e "\n1. Removing any mock Firebase settings..."
sed -i '/USE_MOCK_FIREBASE/d' .env
echo "✅ Cleaned .env file"

echo -e "\n2. Ensuring Firebase credentials path is set..."
if ! grep -q "FIREBASE_CREDENTIALS_PATH" .env; then
    echo "FIREBASE_CREDENTIALS_PATH=/app/firebase-credentials.json" >> .env
    echo "✅ Added FIREBASE_CREDENTIALS_PATH to .env"
else
    echo "✅ FIREBASE_CREDENTIALS_PATH already set"
fi

echo -e "\n3. Forcing Firebase initialization in running container..."
docker exec $CONTAINER_NAME python -c "
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'purplex.settings'
import django
django.setup()

from purplex.users_app.services.authentication_service import AuthenticationService

# Force re-initialization
AuthenticationService._firebase_app = None
try:
    AuthenticationService._initialize_firebase()
    print('✅ Firebase initialized successfully')

    # Verify it's working
    import firebase_admin
    app = firebase_admin.get_app()
    print(f'✅ Firebase app active: {app.name}')
except Exception as e:
    print(f'❌ Failed: {e}')
" 2>&1

echo -e "\n4. Restarting web container..."
docker-compose restart web

echo -e "\n5. Waiting for container to be ready..."
sleep 10

echo -e "\n6. Final verification..."
docker exec $(docker ps --format "{{.Names}}" | grep web | head -1) python -c "
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'purplex.settings'
import django
django.setup()

from purplex.users_app.services.authentication_service import AuthenticationService
import firebase_admin

if AuthenticationService._firebase_app:
    print('✅ Firebase is initialized')
    app = firebase_admin.get_app()
    print(f'✅ Using project: {app.project_id if hasattr(app, \"project_id\") else \"OK\"}')
else:
    print('❌ Firebase still not initialized - may need to rebuild container')
" 2>&1

echo -e "\n========================================="
echo "FIX APPLIED"
echo "========================================="
echo ""
echo "Now try logging in again at http://3.129.89.26:8000"
echo "If it still doesn't work, run: docker-compose down && docker-compose up -d"