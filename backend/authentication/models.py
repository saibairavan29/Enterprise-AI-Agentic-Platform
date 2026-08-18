from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    """
    Custom user model introducing role-based access controls.
    Roles:
      - admin: Complete system control
      - analyst: Can parse data, view reports, simulate impact models
      - reader: Can view dashboards and retrieve assistant queries
    """
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('analyst', 'Analyst'),
        ('reader', 'Reader'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='reader')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Use email as unique identifier or keep username but make email required
    email = models.EmailField(unique=True, help_text="Required. Unique email address.")

    def __str__(self):
        return f"{self.username} - {self.role}"
