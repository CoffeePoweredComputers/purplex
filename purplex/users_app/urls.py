from django.urls import path

from .user_views import (
    AdminUserManagementView,
    AuthStatusView,
    LanguagePreferenceView,
    SSETokenView,
    UserRoleView,
)
from .views.privacy_views import (
    AccountDeletionView,
    AgeVerificationView,
    ConsentListView,
    ConsentWithdrawView,
    DataExportView,
    DirectoryInfoOptOutView,
    NomineeView,
)

urlpatterns = [
    path("user/me/", UserRoleView.as_view(), name="user_role"),
    path(
        "user/me/language/",
        LanguagePreferenceView.as_view(),
        name="language_preference",
    ),
    path("auth/status/", AuthStatusView.as_view(), name="auth_status"),
    path("auth/sse-token/", SSETokenView.as_view(), name="sse_token"),
    path("admin/users/", AdminUserManagementView.as_view(), name="admin_users_list"),
    path(
        "admin/user/<int:user_id>/",
        AdminUserManagementView.as_view(),
        name="admin_user_update",
    ),
    # Privacy & data rights endpoints (GDPR, CCPA, DPDPA)
    path(
        "users/me/data-export/",
        DataExportView.as_view(),
        name="data_export",
    ),
    path(
        "users/me/delete/",
        AccountDeletionView.as_view(),
        name="account_deletion",
    ),
    path(
        "users/me/cancel-deletion/",
        AccountDeletionView.as_view(),
        name="cancel_deletion",
    ),
    path(
        "users/me/consents/",
        ConsentListView.as_view(),
        name="consent_list",
    ),
    path(
        "users/me/consents/<str:consent_type>/",
        ConsentWithdrawView.as_view(),
        name="consent_withdraw",
    ),
    path(
        "users/me/age-verification/",
        AgeVerificationView.as_view(),
        name="age_verification",
    ),
    path(
        "users/me/nominee/",
        NomineeView.as_view(),
        name="nominee",
    ),
    path(
        "users/me/directory-info/",
        DirectoryInfoOptOutView.as_view(),
        name="directory_info",
    ),
]
