from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie


@ensure_csrf_cookie
def csrf_token(request):
    """
    View to get a CSRF token. This sets the CSRF cookie.
    Frontend can call this endpoint to ensure it has a valid CSRF token.
    """
    token = get_token(request)
    return JsonResponse({'csrfToken': token})