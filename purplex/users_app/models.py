from django.contrib.auth.models import User
from django.db import models


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
