from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class UserRole(models.TextChoices):
    ADMIN = "admin", "Admin"
    INSTRUCTOR = "instructor", "Instructor"
    USER = "user", "User"


class LanguageChoice(models.TextChoices):
    ENGLISH = "en", "English"
    HINDI = "hi", "Hindi"
    BENGALI = "bn", "Bengali"
    TELUGU = "te", "Telugu"
    PUNJABI = "pa", "Punjabi"
    MARATHI = "mr", "Marathi"
    KANNADA = "kn", "Kannada"
    TAMIL = "ta", "Tamil"
    JAPANESE = "ja", "Japanese"
    CHINESE = "zh", "Chinese"
    PORTUGUESE = "pt", "Portuguese"
    VIETNAMESE = "vi", "Vietnamese"
    THAI = "th", "Thai"
    SPANISH = "es", "Spanish"
    FRENCH = "fr", "French"
    GERMAN = "de", "German"
    MAORI = "mi", "Māori"


# Extend the User model if needed
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    firebase_uid = models.CharField(max_length=128, unique=True)
    role = models.CharField(
        max_length=10,
        choices=UserRole.choices,
        default=UserRole.USER,
    )
    language_preference = models.CharField(
        max_length=5,
        choices=LanguageChoice.choices,
        default=LanguageChoice.ENGLISH,
        help_text="User's preferred language for UI and AI feedback",
    )

    def __str__(self):
        return self.user.username

    @property
    def is_admin(self):
        return self.role == UserRole.ADMIN

    @property
    def is_instructor(self):
        return self.role == UserRole.INSTRUCTOR

    @property
    def is_instructor_or_admin(self):
        return self.role in [UserRole.INSTRUCTOR, UserRole.ADMIN]

    # FERPA directory information opt-out
    directory_info_visible = models.BooleanField(
        default=True,
        help_text="Whether this user's name/email are visible in course rosters",
    )

    # Soft-delete support for 30-day grace period (GDPR Art. 17)
    deletion_requested_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When account deletion was requested (30-day grace period)",
    )
    deletion_scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When hard deletion is scheduled to occur",
    )


class ConsentType(models.TextChoices):
    PRIVACY_POLICY = "privacy_policy", "Privacy Policy"
    TERMS_OF_SERVICE = "terms_of_service", "Terms of Service"
    AI_PROCESSING = "ai_processing", "AI Code Analysis"
    THIRD_PARTY_SHARING = "third_party_sharing", "Third-Party Data Sharing"
    RESEARCH_USE = "research_use", "Research Data Use"
    BEHAVIORAL_TRACKING = "behavioral_tracking", "Behavioral/Progress Tracking"


class ConsentMethod(models.TextChoices):
    REGISTRATION = "registration", "At Registration"
    IN_APP = "in_app", "In-App Prompt"
    INSTITUTIONAL = "institutional", "Via Institutional Agreement"
    PARENTAL = "parental", "Parental/Guardian Consent"


class UserConsent(models.Model):
    """
    Append-only consent audit trail.
    GDPR Art. 7 requires proof that consent was given.
    Each grant or withdrawal creates a new record.
    Records are never updated or deleted — SET_NULL preserves them when user is removed.
    """

    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="consents"
    )
    consent_type = models.CharField(max_length=50, choices=ConsentType.choices)
    granted = models.BooleanField(default=False)
    granted_at = models.DateTimeField(default=timezone.now)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    policy_version = models.CharField(max_length=20)
    consent_method = models.CharField(max_length=30, choices=ConsentMethod.choices)

    class Meta:
        indexes = [
            models.Index(fields=["user", "consent_type"]),
            models.Index(fields=["consent_type", "granted"]),
        ]
        ordering = ["-granted_at"]

    def save(self, *args, **kwargs):
        """Enforce append-only: existing records cannot be modified."""
        if self.pk and not self._state.adding:
            raise ValueError(
                "UserConsent records are immutable. Create a new record instead."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion of consent records (GDPR Art. 7 audit trail)."""
        raise ValueError(
            "UserConsent records cannot be deleted. They form a legal audit trail."
        )

    def __str__(self):
        username = self.user.username if self.user else "deleted-user"
        status = "granted" if self.granted and not self.withdrawn_at else "withdrawn"
        return f"{username} - {self.consent_type} ({status})"


class VerificationMethod(models.TextChoices):
    SELF_DECLARED = "self_declared", "Self-Declared"
    INSTITUTIONAL = "institutional", "Verified by Institution"
    PARENTAL = "parental", "Parent/Guardian Verified"


class AgeVerification(models.Model):
    """
    Age verification for COPPA (under-13) and DPDPA (under-18) compliance.
    Stored separately from UserProfile to allow independent lifecycle.
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="age_verification"
    )
    date_of_birth = models.DateField(
        null=True,
        blank=True,
        help_text="Optional — only collected if needed for verification",
    )
    is_minor = models.BooleanField(
        help_text="Under 18 (triggers DPDPA children's provisions)"
    )
    is_child = models.BooleanField(help_text="Under 13 (triggers COPPA requirements)")
    verified_at = models.DateTimeField(default=timezone.now)
    verification_method = models.CharField(
        max_length=30, choices=VerificationMethod.choices
    )
    parental_consent_given = models.BooleanField(default=False)
    parental_consent_email = models.EmailField(null=True, blank=True)
    parental_consent_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        label = "child" if self.is_child else ("minor" if self.is_minor else "adult")
        return f"{self.user.username} - {label}"


class AuditAction(models.TextChoices):
    VIEW_USER_LIST = "view_user_list", "Viewed User List"
    SEARCH_USERS = "search_users", "Searched Users"
    EXPORT_RESEARCH = "export_research", "Exported Research Data"
    EXPORT_COURSE = "export_course", "Exported Course Data"
    VIEW_STUDENT_DETAIL = "view_student_detail", "Viewed Student Detail"
    CHANGE_ROLE = "change_role", "Changed User Role"
    DELETE_USER = "delete_user", "Deleted User Account"
    VIEW_SUBMISSIONS = "view_submissions", "Viewed Submissions"
    DATA_EXPORT = "data_export", "User Data Export"


class DataAccessAuditLog(models.Model):
    """
    Audit trail for admin/instructor access to user data.
    Required by FERPA for disclosure records and GDPR Art. 30 for ROPA.
    """

    accessor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="audit_logs"
    )
    action = models.CharField(max_length=50, choices=AuditAction.choices)
    target_user_ids = models.JSONField(default=list, blank=True)
    query_parameters = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    record_count = models.IntegerField(default=0)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["accessor", "-timestamp"]),
            models.Index(fields=["action", "-timestamp"]),
        ]

    def __str__(self):
        accessor_name = self.accessor.username if self.accessor else "deleted-user"
        return f"{accessor_name} - {self.action} at {self.timestamp}"


class DataPrincipalNominee(models.Model):
    """
    DPDPA Sec. 8(7) — Allow nomination of a rights exerciser
    for death or incapacity of the data principal.
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="data_nominee"
    )
    nominee_name = models.CharField(max_length=255)
    nominee_email = models.EmailField()
    nominee_relationship = models.CharField(max_length=100)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return (
            f"{self.user.username} -> {self.nominee_name} ({self.nominee_relationship})"
        )
