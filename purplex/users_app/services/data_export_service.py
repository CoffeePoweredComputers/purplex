"""
User data export service for GDPR Art. 20 (Data Portability)
and CCPA Right to Know compliance.

Exports all user data in a machine-readable JSON format.
"""

import logging

from django.contrib.auth.models import User

from .consent_service import ConsentService

logger = logging.getLogger(__name__)


class DataExportService:
    """Service for exporting all data associated with a user."""

    @staticmethod
    def export_user_data(user: User) -> dict:
        """
        Export all user data in a structured JSON format.
        Covers GDPR Art. 15 (Right of Access) and Art. 20 (Data Portability).
        """
        data = {
            "export_version": "1.0",
            "user_id": user.id,
            "profile": DataExportService._export_profile(user),
            "submissions": DataExportService._export_submissions(user),
            "progress": DataExportService._export_progress(user),
            "enrollments": DataExportService._export_enrollments(user),
            "hint_activations": DataExportService._export_hint_activations(user),
            "ai_analyses": DataExportService._export_ai_analyses(user),
            "consent_history": ConsentService.get_consent_history(user),
        }

        # Include age verification if it exists
        age_verification = getattr(user, "age_verification", None)
        if age_verification:
            data["age_verification"] = {
                "is_minor": age_verification.is_minor,
                "is_child": age_verification.is_child,
                "verified_at": age_verification.verified_at.isoformat(),
                "verification_method": age_verification.verification_method,
                "parental_consent_given": age_verification.parental_consent_given,
            }

        # Include nominee if it exists
        nominee = getattr(user, "data_nominee", None)
        if nominee:
            data["data_nominee"] = {
                "nominee_name": nominee.nominee_name,
                "nominee_email": nominee.nominee_email,
                "nominee_relationship": nominee.nominee_relationship,
            }

        logger.info(f"Data export completed for user {user.username}")
        return data

    @staticmethod
    def _export_profile(user: User) -> dict:
        """Export user profile data."""
        profile_data = {
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "date_joined": user.date_joined.isoformat(),
            "last_login": user.last_login.isoformat() if user.last_login else None,
        }

        profile = getattr(user, "profile", None)
        if profile:
            profile_data.update(
                {
                    "role": profile.role,
                    "language_preference": profile.language_preference,
                    "directory_info_visible": profile.directory_info_visible,
                }
            )

        return profile_data

    @staticmethod
    def _export_submissions(user: User) -> list[dict]:
        """Export all user submissions."""
        from purplex.submissions.models import Submission

        submissions = Submission.objects.filter(user=user).order_by("submitted_at")
        return [
            {
                "submission_id": str(s.submission_id),
                "problem": s.problem.title if s.problem else None,
                "submission_type": s.submission_type,
                "raw_input": s.raw_input,
                "score": s.score,
                "is_correct": s.is_correct,
                "comprehension_level": s.comprehension_level,
                "execution_status": s.execution_status,
                "submitted_at": s.submitted_at.isoformat(),
                "time_spent": str(s.time_spent) if s.time_spent else None,
            }
            for s in submissions
        ]

    @staticmethod
    def _export_progress(user: User) -> list[dict]:
        """Export user progress records."""
        from purplex.problems_app.models import UserProgress

        progress_records = UserProgress.objects.filter(user=user)
        return [
            {
                "problem": p.problem.title if p.problem else None,
                "score": p.score,
                "attempts": p.attempts,
                "is_complete": p.is_complete,
                "completed_at": p.completed_at.isoformat() if p.completed_at else None,
                "time_spent": str(p.time_spent) if p.time_spent else None,
                "hints_used": p.hints_used,
            }
            for p in progress_records
        ]

    @staticmethod
    def _export_enrollments(user: User) -> list[dict]:
        """Export course enrollment data."""
        from purplex.problems_app.models import CourseEnrollment

        enrollments = CourseEnrollment.objects.filter(user=user)
        return [
            {
                "course": e.course.title if e.course else None,
                "course_id": e.course.course_id if e.course else None,
                "enrolled_at": e.enrolled_at.isoformat(),
                "is_active": e.is_active,
            }
            for e in enrollments
        ]

    @staticmethod
    def _export_hint_activations(user: User) -> list[dict]:
        """Export hint activation records."""
        from purplex.submissions.models import HintActivation

        activations = HintActivation.objects.filter(
            submission__user=user
        ).select_related("hint", "submission")
        return [
            {
                "submission_id": str(a.submission.submission_id),
                "hint_type": a.hint.hint_type if a.hint else None,
                "activated_at": a.activated_at.isoformat(),
                "trigger_type": a.trigger_type,
                "viewed_duration_seconds": a.viewed_duration_seconds,
                "was_helpful": a.was_helpful,
            }
            for a in activations
        ]

    @staticmethod
    def _export_ai_analyses(user: User) -> list[dict]:
        """Export AI segmentation analysis results."""
        from purplex.submissions.models import SegmentationAnalysis

        analyses = SegmentationAnalysis.objects.filter(
            submission__user=user
        ).select_related("submission")
        return [
            {
                "submission_id": str(a.submission.submission_id),
                "segment_count": a.segment_count,
                "comprehension_level": a.comprehension_level,
                "confidence_score": a.confidence_score,
                "feedback_message": a.feedback_message,
                "passed": a.passed,
            }
            for a in analyses
        ]
