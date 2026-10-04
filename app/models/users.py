import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager

from app.models.tenants import TenantProfile


class UserManager(BaseUserManager):
    def get_queryset(self):
        from middleware.utils import get_current_tenant_id
        tenant_id = get_current_tenant_id()
        if tenant_id:
            return super().get_queryset().filter(tenant_id=tenant_id)
        return super().get_queryset()

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    ROLE_CHOICES = [
        ('tenant', 'Tenant'),
        ('staff', 'Staff'),
    ]
    
    email = models.EmailField(unique=True)
    tenant = models.ForeignKey(TenantProfile, on_delete=models.CASCADE, related_name='users', null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    @property
    def display_name(self):
        first = self.first_name
        last = self.last_name
        if not (first or last):
            try:
                if hasattr(self, 'profile') and self.profile:
                    first = self.profile.first_name
                    last = self.profile.last_name
            except Exception:
                pass
        full_name = f"{first or ''} {last or ''}".strip()
        if full_name:
            return full_name
        if self.email:
            return self.email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
        return "Staff"

    @property
    def username(self):
        return self.display_name

    @username.setter
    def username(self, value):
        # Allow assignment without error if external Django logic sets user.username
        pass

    def get_full_name(self):
        return self.display_name

    def get_short_name(self):
        return self.first_name or (self.email.split('@')[0].title() if self.email else "Staff")

    def save(self, *args, **kwargs):
        if not self.tenant_id:
            from middleware.utils import get_current_tenant_id
            tenant_id = get_current_tenant_id()
            if tenant_id:
                self.tenant_id = tenant_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.email} ({self.tenant.name if self.tenant else 'No Tenant'})"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email}'s Profile"
