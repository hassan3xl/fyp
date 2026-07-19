from django.db import models
from middleware.utils import get_current_tenant_id

class TenantScopedManager(models.Manager):
    def get_queryset(self):
        tenant_id = get_current_tenant_id()
        # Automatically isolate queries at the database queryset level if a tenant is active
        if tenant_id:
            return super().get_queryset().filter(tenant_id=tenant_id)
        return super().get_queryset()

class TenantIsolatedModel(models.Model):
    # This abstract base class enforces application-layer resource isolation.
    # It automatically wires up the TenantScopedManager and auto-populates
    # the tenant_id when saving new objects.
    
    # We use objects as the default tenant-isolated manager
    objects = TenantScopedManager()
    
    # We provide a clean escape-hatch for system-wide/unscoped queries (e.g. admin tasks)
    unscoped_objects = models.Manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # Automatically inject the current tenant's ID into the model instance
        if not getattr(self, 'tenant_id', None):
            tenant_id = get_current_tenant_id()
            if tenant_id:
                self.tenant_id = tenant_id
        super().save(*args, **kwargs)
