from rest_framework import authentication, exceptions
from django.contrib.auth.models import User
from django.conf import settings
from firebase_admin import auth, credentials, initialize_app
import os
import firebase_admin
from .models import UserProfile

# Initialize Firebase Admin SDK
try:
    cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
    firebase_admin_app = initialize_app(cred)
except (firebase_admin.exceptions.FirebaseError, ValueError) as e:
    print(f"Firebase initialization error: {e}")
    firebase_admin_app = None

class FirebaseAuthentication(authentication.BaseAuthentication):
    """
    Custom authentication for Firebase that synchronizes users with Django
    """
    def authenticate(self, request):
        # Get the auth header from the request
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        # Check if auth header exists and starts with 'Bearer'
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
            
        # Get the Firebase ID token
        firebase_token = auth_header.split(' ')[1]
        
        # Verify the token
        try:
            decoded_token = auth.verify_id_token(firebase_token)
            firebase_uid = decoded_token['uid']
            email = decoded_token.get('email', '')
            display_name = decoded_token.get('name', '')
            
            # Try to get the user from UserProfile
            try:
                user_profile = UserProfile.objects.get(firebase_uid=firebase_uid)
                user = user_profile.user
                
                # Update user data if changed in Firebase
                updated = False
                if email and user.email != email:
                    user.email = email
                    updated = True
                    
                if display_name and user.first_name != display_name:
                    user.first_name = display_name
                    updated = True
                    
                if updated:
                    user.save()
                    
                # Return existing user
                return (user, None)
                
            except UserProfile.DoesNotExist:
                # Create new Django user and profile
                username = email.split('@')[0] if email else firebase_uid[:15]
                
                # Ensure username is unique
                existing_count = User.objects.filter(username__startswith=username).count()
                if existing_count > 0:
                    username = f"{username}{existing_count}"
                
                # Create the Django user
                user = User.objects.create(
                    username=username,
                    email=email or '',
                    first_name=display_name or ''
                )
                
                # Create the UserProfile
                user_profile = UserProfile.objects.create(
                    user=user,
                    firebase_uid=firebase_uid,
                    role='user'  # Default role
                )
                
                print(f"Created new user {username} with Firebase UID {firebase_uid}")
                return (user, None)
                
        except auth.InvalidIdTokenError:
            raise exceptions.AuthenticationFailed('Invalid Firebase ID token')
        except auth.ExpiredIdTokenError:
            raise exceptions.AuthenticationFailed('Expired Firebase ID token')
        except Exception as e:
            print(f"Firebase authentication error: {e}")
            return None

class DebugAuthentication(authentication.BaseAuthentication):
    """
    Custom authentication for debug mode that accepts any token
    """
    def authenticate(self, request):
        # Only active in debug mode
        if not settings.DEBUG:
            return None

        auth_header = request.META.get('HTTP_AUTHORIZATION', '').split()

        if not auth_header or auth_header[0].lower() != 'bearer':
            pass

        if len(auth_header) >= 2:
            try:
                user = User.objects.get(username='anavarre')
                print(f"DEBUG: Authenticated as {user.username} (superuser: {user.is_superuser}, staff: {user.is_staff})")
                return (user, None)
            except User.DoesNotExist:

                try:
                    user = User.objects.first()
                    if user:
                        print(f"DEBUG: Authenticated as first user {user.username}")
                        return (user, None)
                except:
                    pass

                user = User(
                            username='debug_user',
                            is_staff=True,
                            is_superuser=True
                        )
                print("DEBUG: Created temporary debug_user")
                return (user, None)

        if settings.DEBUG:
            try:
                user = User.objects.first()
                if user:
                    print(f"DEBUG: Auto-authenticated as first user {user.username}")
                    return (user, None)
            except:
                pass

            user = User(
                        username='debug_user',
                        is_staff=True,
                        is_superuser=True
                    )
            print("DEBUG: Created temporary debug_user (no auth header)")
            return (user, None)

        return None
