from django.contrib.auth.models import User
from rest_framework import serializers

from .models import UserProfile


class MinimalUserSerializer(serializers.ModelSerializer):
    """
    Data-minimized user serializer (GDPR Art. 25 — Privacy by Design).
    Use in contexts where full PII isn't needed: course rosters,
    public-facing responses, enrollment lists.
    """

    class Meta:
        model = User
        fields = ["id", "username"]
        read_only_fields = ["id"]


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Full profile serializer — only for the profile owner or admin views.
    firebase_uid is excluded from non-owner responses.
    """

    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "username",
            "email",
            "role",
            "language_preference",
            "directory_info_visible",
        ]
        read_only_fields = ["id"]


class UserProfileOwnerSerializer(serializers.ModelSerializer):
    """
    Profile serializer that includes firebase_uid — only for the profile owner.
    """

    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "username",
            "email",
            "role",
            "firebase_uid",
            "language_preference",
            "directory_info_visible",
        ]
        read_only_fields = ["id", "firebase_uid"]


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "profile"]
        read_only_fields = ["id"]
