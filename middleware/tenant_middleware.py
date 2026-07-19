from django.shortcuts import redirect
from django.http import Http404
from django.urls import resolve, Resolver404
from app.models.tenants import Tenant
from .utils import get_current_tenant_id, set_current_tenant_id, clear_current_tenant


class TenantIsolationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        clear_current_tenant()

        exempt_paths = ['/register/', '/logout/', '/admin/', '/static/', '/onboarding/']
        is_exempt = any(request.path.startswith(path) for path in exempt_paths) or request.path == '/'

        try:
            match = resolve(request.path_info)
            tenant_slug = match.kwargs.get('tenant_slug')
        except Resolver404:
            tenant_slug = None

        if tenant_slug:
            try:
                tenant = Tenant.objects.get(slug=tenant_slug)
            except Tenant.DoesNotExist:
                raise Http404('Tenant does not exist')

            if request.user.is_authenticated:
                user_tenant = getattr(request.user, 'tenant', None)
                if user_tenant and user_tenant != tenant:
                    raise Http404('Access denied to this workspace')
                if user_tenant and not user_tenant.is_onboarded:
                    return redirect('/onboarding/')
            else:
                return redirect('/')

            request.tenant_id = str(tenant.id)
            request.business_type = tenant.business_type
            request.plan = tenant.plan
            request.tenant_name = tenant.name
            request.tenant_slug = tenant.slug
            set_current_tenant_id(str(tenant.id))
        else:
            if request.user.is_authenticated:
                user_tenant = getattr(request.user, 'tenant', None)
                if user_tenant:
                    if not user_tenant.is_onboarded and request.path != '/onboarding/' and not is_exempt:
                        return redirect('/onboarding/')
                    elif user_tenant.is_onboarded and request.path == '/':
                        return redirect(f'/{user_tenant.slug}/')

            request.tenant_id = None
            request.business_type = None
            request.plan = None
            request.tenant_name = None
            request.tenant_slug = None

            if not is_exempt and not request.user.is_authenticated:
                return redirect('/')

        response = self.get_response(request)
        clear_current_tenant()
        return response


class TenantThrottleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        exempt_paths = ['/register/', '/logout/', '/admin/', '/static/', '/onboarding/']
        is_exempt = any(request.path.startswith(path) for path in exempt_paths) or request.path == '/'

        if is_exempt:
            return self.get_response(request)

        tenant_id = getattr(request, 'tenant_id', None)
        plan = getattr(request, 'plan', 'standard')

        if not tenant_id:
            return self.get_response(request)

        from django.core.cache import cache
        import time

        limit = 300 if plan == 'premium' else 100
        window_start = int(time.time() // 60) * 60
        cache_key = f'throttle:{tenant_id}:{window_start}'

        count = cache.get_or_set(cache_key, 0, timeout=120)
        count = cache.incr(cache_key)

        if count > limit:
            retry_after = 60 - int(time.time() % 60)
            if retry_after <= 0:
                retry_after = 60

            from django.template import loader
            from django.http import HttpResponse

            try:
                template = loader.get_template('429.html')
                content = template.render({'retry_after': retry_after})
            except Exception:
                content = f'<h1>429 Too Many Requests</h1><p>Rate limit exceeded. Please try again after {retry_after} seconds.</p>'

            response = HttpResponse(content, status=429)
            response['Retry-After'] = str(retry_after)
            return response

        return self.get_response(request)
