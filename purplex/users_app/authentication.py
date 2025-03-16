from rest_framework import authentication
from django.contrib.auth.models import User
from django.conf import settings

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
