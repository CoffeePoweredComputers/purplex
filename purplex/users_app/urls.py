from django.urls import path
from .views import AIGenerateView, UserRoleView, AdminUserManagementView, AuthStatusView

urlpatterns = [
    path('generate/', AIGenerateView.as_view(), name='ai_generate'),
    path('user/me/', UserRoleView.as_view(), name='user_role'),
    path('auth/status/', AuthStatusView.as_view(), name='auth_status'),
    path('admin/users/', AdminUserManagementView.as_view(), name='admin_users_list'),
    path('admin/user/<int:user_id>/', AdminUserManagementView.as_view(), name='admin_user_update'),
]