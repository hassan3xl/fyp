def tenant_context(request):
    return {
        'tenant_id': getattr(request, 'tenant_id', None),
        'business_type': getattr(request, 'business_type', None),
        'tenant_name': getattr(request, 'tenant_name', None),
        'tenant_slug': getattr(request, 'tenant_slug', None),
        'plan': getattr(request, 'plan', None),
    }
