from django.db import models
from django.contrib.auth.models import User

class UserRole(models.TextChoices):
    ADMIN = 'admin', 'Admin'
    USER = 'user', 'User'

# Extend the User model if needed
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    firebase_uid = models.CharField(max_length=128, unique=True)
    role = models.CharField(
        max_length=10,
        choices=UserRole.choices,
        default=UserRole.USER,
    )
    
    def __str__(self):
        return self.user.username
    
    @property
    def is_admin(self):
        return self.role == UserRole.ADMIN