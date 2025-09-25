from django.urls import path
from .user_views import (
    AIGenerateView, 
    UserRoleView, 
    AdminUserManagementView, 
    AuthStatusView,
    SSETokenView
)

urlpatterns = [
    path('generate/', AIGenerateView.as_view(), name='ai_generate'),
    path('user/me/', UserRoleView.as_view(), name='user_role'),
    path('auth/status/', AuthStatusView.as_view(), name='auth_status'),
    path('auth/sse-token/', SSETokenView.as_view(), name='sse_token'),
    path('admin/users/', AdminUserManagementView.as_view(), name='admin_users_list'),
    path('admin/user/<int:user_id>/', AdminUserManagementView.as_view(), name='admin_user_update'),
]