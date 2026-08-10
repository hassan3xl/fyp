import time
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.template import loader

class ThrottleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Exempt certain paths from throttling
        exempt_paths = ['/register/', '/logout/', '/admin/', '/static/', '/onboarding/', '/ping/']
        is_exempt = any(request.path.startswith(path) for path in exempt_paths) or request.path == '/'

        if is_exempt:
            return self.get_response(request)

        # Check for session-based bypass to prevent redirect loops when displaying messages/modals
        session = getattr(request, 'session', None)
        if session and session.get('throttled_bypass'):
            # Consume the bypass token for this request
            session.pop('throttled_bypass', None)
            return self.get_response(request)

        # Identify client by tenant_id if present, otherwise by client IP address
        tenant_id = getattr(request, 'tenant_id', None)
        if tenant_id:
            identifier = f"tenant:{tenant_id}"
        else:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                identifier = f"ip:{x_forwarded_for.split(',')[0].strip()}"
            else:
                identifier = f"ip:{request.META.get('REMOTE_ADDR')}"

        plan = getattr(request, 'plan', 'standard')
        default_limit = 300 if str(plan).lower() == 'premium' else 100
        limit = getattr(settings, 'THROTTLE_LIMIT', default_limit)
        window_size = 60
        cache_key = f'throttle:{identifier}'

        now = time.time()
        timestamps = cache.get(cache_key, [])

        # Filter out timestamps older than the sliding window
        timestamps = [t for t in timestamps if t > now - window_size]

        if len(timestamps) >= limit:
            oldest = timestamps[0]
            retry_after = int(oldest + window_size - now)
            if retry_after <= 0:
                retry_after = 1

            # Check if AJAX or JSON request
            is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('accept', '')
            if is_ajax:
                from django.http import JsonResponse
                response = JsonResponse({
                    'error': 'Rate limit exceeded',
                    'retry_after': retry_after
                }, status=429)
                response['Retry-After'] = str(retry_after)
                return response

            # Standard request: Add a Django message and redirect to show a modal/popup
            from django.contrib import messages
            from django.shortcuts import redirect

            messages.error(
                request,
                "Rate limit exceeded.",
                extra_tags=f"rate-limit-{retry_after}"
            )

            # Set bypass flag for the next immediate request (the redirect)
            if session is not None:
                session['throttled_bypass'] = True

            # Redirect to the referrer or the current path as a fallback
            redirect_url = request.META.get('HTTP_REFERER') or request.path
            response = redirect(redirect_url)
            response['Retry-After'] = str(retry_after)
            return response

        # Add the current timestamp and save back to the cache
        timestamps.append(now)
        cache.set(cache_key, timestamps, timeout=window_size)

        return self.get_response(request)

# Keep TenantThrottleMiddleware alias for backward compatibility
TenantThrottleMiddleware = ThrottleMiddleware
