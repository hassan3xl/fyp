import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager


class TenantProfile(models.Model):
    BUSINESS_TYPE_CHOICES = [
        ('pharmacy', 'Pharmacy'),
        ('provision_store', 'Provision Store'),
        ('supermarket', 'Supermarket'),
        ('electronic_store', 'Electronic Store'),
    ]
    PLAN_CHOICES = [
        ('standard', 'Standard'),
        ('premium', 'Premium'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    business_type = models.CharField(max_length=50, choices=BUSINESS_TYPE_CHOICES, blank=True, null=True)
    slug = models.SlugField(unique=True)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='standard')
    is_onboarded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
# Keep legacy model name compatibility for code that imports Tenant
Tenant = TenantProfile
