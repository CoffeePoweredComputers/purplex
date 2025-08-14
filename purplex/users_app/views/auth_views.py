"""
Authentication-related views for secure token exchange.
"""
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from purplex.users_app.authentication import PurplexAuthentication
from purplex.users_app.services.authentication_service import AuthenticationService
from purplex.users_app.services.rate_limit_service import RateLimitService
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@authentication_classes([PurplexAuthentication])
@permission_classes([IsAuthenticated])
def create_sse_token(request):
    """
    Exchange a valid Firebase token for a short-lived SSE session token.
    
    This endpoint prevents token exposure in URLs by providing temporary
    session tokens specifically for SSE connections.
    
    Returns:
        JSON response with SSE session token
    """
    try:
        # User is already authenticated via PurplexAuthentication
        user = request.user
        
        # Check rate limit for SSE token creation
        if not RateLimitService.check_sse_token_rate_limit(user.id):
            logger.warning(f"SSE token rate limit exceeded for user {user.username}")
            return Response({
                'error': 'Rate limit exceeded. Please wait before requesting another token.'
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Create SSE session token
        session_token = AuthenticationService.create_sse_session(user)
        
        return Response({
            'sse_token': session_token,
            'expires_in': 300  # 5 minutes
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Failed to create SSE token: {e}")
        return Response({
            'error': 'Failed to create session token'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@authentication_classes([PurplexAuthentication])
@permission_classes([IsAuthenticated])
def revoke_sse_token(request):
    """
    Revoke an SSE session token.
    
    This allows clients to explicitly clean up sessions.
    
    Returns:
        JSON response indicating success
    """
    try:
        sse_token = request.data.get('sse_token')
        
        if not sse_token:
            return Response({
                'error': 'SSE token required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Revoke the session
        revoked = AuthenticationService.revoke_sse_session(sse_token)
        
        if revoked:
            return Response({
                'message': 'Session revoked successfully'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'message': 'Session not found or already expired'
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        logger.error(f"Failed to revoke SSE token: {e}")
        return Response({
            'error': 'Failed to revoke session'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@authentication_classes([PurplexAuthentication])
@permission_classes([IsAuthenticated])
def auth_status(request):
    """
    Check authentication status.
    
    Returns:
        JSON response with user information if authenticated
    """
    try:
        return Response({
            'authenticated': True,
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
                'role': getattr(request.user.userprofile, 'role', 'user') if hasattr(request.user, 'userprofile') else 'user'
            }
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error checking auth status: {e}")
        return Response({
            'authenticated': False,
            'error': 'Failed to check authentication status'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)