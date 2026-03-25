from django.db import models
from django.contrib.auth.models import AbstractUser
import secrets
from django.utils import timezone
from datetime import timedelta


class User(AbstractUser):
    ROLE_CHOICES=(
        ('patient','Patient'),
        ('doctor','Doctor'),

    )
    role =models.CharField(max_length=50,choices=ROLE_CHOICES,default='patient')
    phone =models.CharField(max_length=15,blank=True)
    date_of_birth= models.DateField(null=True,blank=True)
    email_digest_enabled=models.BooleanField(default=True)
    email = models.EmailField(unique=True, blank=False)
    assigned_doctor = models.ForeignKey(
        'self',
        on_delete= models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_patients',
        limit_choices_to={'role':'doctor'}
    )


    def __str__(self):
        return f"{self.username} ({self.role})"


class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(48)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=1)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        return not self.used and timezone.now() < self.expires_at

    def __str__(self):
        return f"ResetToken for {self.user.username} ({'used' if self.used else 'valid' if self.is_valid else 'expired'})"