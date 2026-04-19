"""
Privacy and data rights views.

Implements endpoints for:
- GDPR Art. 15 (Right of Access) / Art. 20 (Data Portability)
- GDPR Art. 17 (Right to Erasure)
- GDPR Art. 7 / DPDPA Sec. 4 (Consent Management)
- CCPA Right to Know / Right to Delete
- DPDPA Sec. 8(7) (Nomination)
"""

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from purplex.utils.error_codes import ErrorCode, error_response

from ..models import (
    AgeVerification,
    AuditAction,
    ConsentMethod,
    ConsentType,
    DataAccessAuditLog,
    DataPrincipalNominee,
    VerificationMethod,
)
from ..permissions import IsAuthenticated
from ..services.consent_service import ConsentService
from ..services.data_deletion_service import DataDeletionService
from ..services.data_export_service import DataExportService
from ..utils.request_helpers import get_client_ip as _get_client_ip

logger = logging.getLogger(__name__)

# Only self-service consent methods can be supplied by the client.
# INSTITUTIONAL and PARENTAL imply a third party granted consent and must be
# set server-side via other code paths.
ALLOWED_SELF_SERVICE_CONSENT_METHODS = frozenset(
    [ConsentMethod.REGISTRATION, ConsentMethod.IN_APP]
)


class DataExportView(APIView):
    """
    GET /api/users/me/data-export/
    Export all user data in machine-readable JSON format.
    GDPR Art. 15 + Art. 20, CCPA Right to Know.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        ip = _get_client_ip(request)

        # Audit log
        DataAccessAuditLog.objects.create(
            accessor=user,
            action=AuditAction.DATA_EXPORT,
            target_user_ids=[user.id],
            ip_address=ip,
        )

        data = DataExportService.export_user_data(user)

        return Response(data, status=status.HTTP_200_OK)


class AccountDeletionView(APIView):
    """
    DELETE /api/users/me/  — Request account deletion (30-day grace period)
    POST /api/users/me/cancel-deletion/  — Cancel pending deletion
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request):
        """Request account deletion with grace period."""
        user = request.user
        ip = _get_client_ip(request)

        try:
            result = DataDeletionService.request_deletion(user)

            DataAccessAuditLog.objects.create(
                accessor=user,
                action=AuditAction.DELETE_USER,
                target_user_ids=[user.id],
                query_parameters={"phase": "soft_delete_requested"},
                ip_address=ip,
            )

            return Response(result, status=status.HTTP_200_OK)

        except ValueError as e:
            return error_response(
                str(e), ErrorCode.VALIDATION_ERROR, status.HTTP_400_BAD_REQUEST
            )

    def post(self, request):
        """Cancel a pending deletion."""
        user = request.user

        result = DataDeletionService.cancel_deletion(user)
        return Response(result, status=status.HTTP_200_OK)


class ConsentListView(APIView):
    """
    GET /api/users/me/consents/  — List current consent status
    POST /api/users/me/consents/  — Grant consent
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get current consent status for all types."""
        consents = ConsentService.get_all_consent_status(request.user)
        return Response(consents, status=status.HTTP_200_OK)

    def post(self, request):
        """Grant consent for a specific type."""
        consent_type = request.data.get("consent_type")
        consent_method = request.data.get("consent_method", ConsentMethod.REGISTRATION)
        ip = _get_client_ip(request)

        if not consent_type:
            return error_response(
                "consent_type is required",
                ErrorCode.VALIDATION_ERROR,
                status.HTTP_400_BAD_REQUEST,
            )

        valid_types = [ct[0] for ct in ConsentType.choices]
        if consent_type not in valid_types:
            return error_response(
                f"Invalid consent_type. Must be one of: {valid_types}",
                ErrorCode.VALIDATION_ERROR,
                status.HTTP_400_BAD_REQUEST,
            )

        # isinstance check guards against non-hashable JSON values (list/dict),
        # which would otherwise raise TypeError on the frozenset membership test
        # and surface as a 500 via the exception handler's catch-all.
        if (
            not isinstance(consent_method, str)
            or consent_method not in ALLOWED_SELF_SERVICE_CONSENT_METHODS
        ):
            return error_response(
                "Invalid consent_method. Must be 'registration' or 'in_app'.",
                ErrorCode.VALIDATION_ERROR,
                status.HTTP_400_BAD_REQUEST,
            )

        consent = ConsentService.grant_consent(
            user=request.user,
            consent_type=consent_type,
            ip_address=ip,
            consent_method=consent_method,
        )

        return Response(
            {
                "consent_type": consent.consent_type,
                "granted": consent.granted,
                "granted_at": consent.granted_at.isoformat(),
                "policy_version": consent.policy_version,
            },
            status=status.HTTP_201_CREATED,
        )


class ConsentWithdrawView(APIView):
    """
    DELETE /api/users/me/consents/<consent_type>/  — Withdraw consent
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, consent_type):
        """Withdraw consent for a specific type."""
        valid_types = [ct[0] for ct in ConsentType.choices]
        if consent_type not in valid_types:
            return error_response(
                f"Invalid consent_type. Must be one of: {valid_types}",
                ErrorCode.VALIDATION_ERROR,
                status.HTTP_400_BAD_REQUEST,
            )

        ip = _get_client_ip(request)
        consent = ConsentService.withdraw_consent(
            user=request.user,
            consent_type=consent_type,
            ip_address=ip,
        )

        return Response(
            {
                "consent_type": consent.consent_type,
                "granted": False,
                "withdrawn_at": consent.withdrawn_at.isoformat(),
            },
            status=status.HTTP_200_OK,
        )


class AgeVerificationView(APIView):
    """
    POST /api/users/me/age-verification/  — Submit age verification
    GET /api/users/me/age-verification/  — Get current verification status
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get current age verification status."""
        try:
            av = request.user.age_verification
            return Response(
                {
                    "is_minor": av.is_minor,
                    "is_child": av.is_child,
                    "verified_at": av.verified_at.isoformat(),
                    "verification_method": av.verification_method,
                    "parental_consent_given": av.parental_consent_given,
                },
                status=status.HTTP_200_OK,
            )
        except AgeVerification.DoesNotExist:
            return Response(
                {"verified": False},
                status=status.HTTP_200_OK,
            )

    def post(self, request):
        """Submit age verification."""
        date_of_birth = request.data.get("date_of_birth")
        is_minor = request.data.get("is_minor", False)
        is_child = request.data.get("is_child", False)

        # Validate date_of_birth format if provided
        if date_of_birth is not None:
            from datetime import date, datetime

            if isinstance(date_of_birth, str):
                try:
                    parsed = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
                    if parsed > date.today():
                        return error_response(
                            "date_of_birth cannot be in the future",
                            ErrorCode.VALIDATION_ERROR,
                            status.HTTP_400_BAD_REQUEST,
                        )
                    date_of_birth = parsed
                except ValueError:
                    return error_response(
                        "date_of_birth must be in YYYY-MM-DD format",
                        ErrorCode.VALIDATION_ERROR,
                        status.HTTP_400_BAD_REQUEST,
                    )

        # Validate boolean fields
        if not isinstance(is_minor, bool):
            return error_response(
                "is_minor must be a boolean",
                ErrorCode.VALIDATION_ERROR,
                status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(is_child, bool):
            return error_response(
                "is_child must be a boolean",
                ErrorCode.VALIDATION_ERROR,
                status.HTTP_400_BAD_REQUEST,
            )

        av, created = AgeVerification.objects.update_or_create(
            user=request.user,
            defaults={
                "date_of_birth": date_of_birth,
                "is_minor": is_minor,
                "is_child": is_child,
                "verification_method": VerificationMethod.SELF_DECLARED,
            },
        )

        return Response(
            {
                "is_minor": av.is_minor,
                "is_child": av.is_child,
                "verified_at": av.verified_at.isoformat(),
                "verification_method": av.verification_method,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class NomineeView(APIView):
    """
    GET/POST/DELETE /api/users/me/nominee/
    DPDPA Sec. 8(7) — Nomination of rights exerciser.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get current nominee."""
        try:
            nominee = request.user.data_nominee
            return Response(
                {
                    "nominee_name": nominee.nominee_name,
                    "nominee_email": nominee.nominee_email,
                    "nominee_relationship": nominee.nominee_relationship,
                },
                status=status.HTTP_200_OK,
            )
        except DataPrincipalNominee.DoesNotExist:
            return Response(
                {"nominee": None},
                status=status.HTTP_200_OK,
            )

    def post(self, request):
        """Set or update nominee."""
        name = request.data.get("nominee_name")
        email = request.data.get("nominee_email")
        relationship = request.data.get("nominee_relationship")

        if not all([name, email, relationship]):
            return error_response(
                "nominee_name, nominee_email, and nominee_relationship are required",
                ErrorCode.VALIDATION_ERROR,
                status.HTTP_400_BAD_REQUEST,
            )

        # Validate email format
        from django.core.exceptions import ValidationError as DjangoValidationError
        from django.core.validators import validate_email

        try:
            validate_email(email)
        except DjangoValidationError:
            return error_response(
                "nominee_email must be a valid email address",
                ErrorCode.VALIDATION_ERROR,
                status.HTTP_400_BAD_REQUEST,
            )

        nominee, created = DataPrincipalNominee.objects.update_or_create(
            user=request.user,
            defaults={
                "nominee_name": name,
                "nominee_email": email,
                "nominee_relationship": relationship,
            },
        )

        return Response(
            {
                "nominee_name": nominee.nominee_name,
                "nominee_email": nominee.nominee_email,
                "nominee_relationship": nominee.nominee_relationship,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request):
        """Remove nominee."""
        try:
            request.user.data_nominee.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except DataPrincipalNominee.DoesNotExist:
            return error_response(
                "No nominee to delete",
                ErrorCode.NOT_FOUND,
                status.HTTP_404_NOT_FOUND,
            )


class DirectoryInfoOptOutView(APIView):
    """
    PATCH /api/users/me/directory-info/
    FERPA directory information opt-out.
    """

    permission_classes = [IsAuthenticated]

    def patch(self, request):
        """Toggle directory information visibility."""
        visible = request.data.get("directory_info_visible")
        if visible is None:
            return error_response(
                "directory_info_visible is required",
                ErrorCode.VALIDATION_ERROR,
                status.HTTP_400_BAD_REQUEST,
            )

        profile = getattr(request.user, "profile", None)
        if not profile:
            return error_response(
                "User profile not found",
                ErrorCode.NOT_FOUND,
                status.HTTP_404_NOT_FOUND,
            )

        profile.directory_info_visible = bool(visible)
        profile.save(update_fields=["directory_info_visible"])

        return Response(
            {"directory_info_visible": profile.directory_info_visible},
            status=status.HTTP_200_OK,
        )
