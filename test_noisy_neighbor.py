import os
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics

# Setup Django environment to programmatically obtain valid Session IDs for tenant users
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings.dev')
import django
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY
from django.core.cache import cache
from app.models.tenants import Tenant

User = get_user_model()

BASE_URL = "http://127.0.0.1:8000"

def get_user_session_cookie(email):
    """Helper to generate a valid Django session cookie for a given user email."""
    try:
        user = User.objects.get(email=email)
        session = SessionStore()
        session[SESSION_KEY] = str(user.pk)
        session[BACKEND_SESSION_KEY] = 'django.contrib.auth.backends.ModelBackend'
        session[HASH_SESSION_KEY] = user.get_session_auth_hash()
        session.save()
        return user, f"sessionid={session.session_key}"
    except User.DoesNotExist:
        return None, None

def make_request(url, cookie=None, client_name=""):
    headers = {"Accept": "application/json"}
    if cookie:
        headers["Cookie"] = cookie

    req = urllib.request.Request(url, headers=headers)
    start = time.perf_counter()
    status_code = None
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            status_code = response.status
            _ = response.read()
    except urllib.error.HTTPError as e:
        status_code = e.code
    except Exception as e:
        status_code = f"ERR ({e})"
    
    elapsed = (time.perf_counter() - start) * 1000  # ms
    return client_name, status_code, elapsed

def run_test(num_tenant_a_reqs=25, num_tenant_b_reqs=3, concurrency=10):
    # Fetch two distinct tenant users from the DB
    users_with_tenants = User.objects.filter(tenant__isnull=False).select_related('tenant')[:2]
    
    if len(users_with_tenants) < 2:
        print("ERROR: Need at least 2 users assigned to different tenants in the DB to test multi-tenancy.")
        return

    user_a, cookie_a = get_user_session_cookie(users_with_tenants[0].email)
    user_b, cookie_b = get_user_session_cookie(users_with_tenants[1].email)

    tenant_a_slug = user_a.tenant.slug
    tenant_b_slug = user_b.tenant.slug

    endpoint_a = f"{BASE_URL}/{tenant_a_slug}/"
    endpoint_b = f"{BASE_URL}/{tenant_b_slug}/"

    # Reset cache across script and server (shared FileBasedCache)
    cache.clear()

    print("=" * 65)
    print(" AUTHENTICATED MULTI-TENANT THROTTLING & NOISY NEIGHBOR TEST")
    print("=" * 65)
    print(f"Target Server: {BASE_URL}")
    print(f"Tenant A (Noisy): Slug='{tenant_a_slug}', User='{user_a.email}' ({num_tenant_a_reqs} reqs)")
    print(f"Tenant B (Normal): Slug='{tenant_b_slug}', User='{user_b.email}' ({num_tenant_b_reqs} reqs)")
    print(f"Concurrency Pool: {concurrency}")
    print("-" * 65)

    # Phase 1: Baseline for Tenant B
    print("\nPhase 1: Measuring Tenant B Baseline (Idle Server)...")
    baseline_latencies = []
    for _ in range(num_tenant_b_reqs):
        _, status, duration = make_request(endpoint_b, cookie_b, client_name="Tenant B")
        if status == 200:
            baseline_latencies.append(duration)
        time.sleep(0.05)
    
    if baseline_latencies:
        avg_base = statistics.mean(baseline_latencies)
        print(f"Tenant B Baseline - Min: {min(baseline_latencies):.2f}ms | Avg: {avg_base:.2f}ms | Max: {max(baseline_latencies):.2f}ms")
    else:
        avg_base = 0
        print("Warning: Tenant B baseline requests did not return 200 OK.")

    # Reset cache so Tenant B starts Phase 2 with a 100% clean rate limit quota
    cache.clear()

    # Phase 2: Concurrent Heavy Burst from Tenant A + Timed Tenant B
    print("\nPhase 2: Executing Concurrent Load (Tenant A Spamming vs Tenant B)...")
    
    tasks = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        # Submit Tenant A burst (25 requests -> will get throttled after 10)
        for i in range(num_tenant_a_reqs):
            tasks.append(executor.submit(make_request, endpoint_a, cookie_a, f"Tenant A (#{i+1})"))
        
        # Submit Tenant B requests concurrently (3 requests -> well under limit of 10)
        for j in range(num_tenant_b_reqs):
            tasks.append(executor.submit(make_request, endpoint_b, cookie_b, f"Tenant B (#{j+1})"))

    tenant_a_results = []
    tenant_b_results = []

    for future in as_completed(tasks):
        client_name, status, duration = future.result()
        if "Tenant A" in client_name:
            tenant_a_results.append((status, duration))
        else:
            tenant_b_results.append((status, duration))

    # Phase 3: Reporting & Analysis
    print("\n" + "=" * 65)
    print(" RESULTS REPORT")
    print("=" * 65)

    a_statuses = {}
    for status, _ in tenant_a_results:
        a_statuses[status] = a_statuses.get(status, 0) + 1
    
    b_statuses = {}
    b_latencies = []
    for status, duration in tenant_b_results:
        b_statuses[status] = b_statuses.get(status, 0) + 1
        if status == 200:
            b_latencies.append(duration)

    print("\n[Tenant A - High Volume / Noisy Neighbor]")
    print(f"Status Code Breakdown: {a_statuses}")
    if 429 in a_statuses or 302 in a_statuses:
        print(" SUCCESS: Tenant A was throttled (Rate limit exceeded)!")
    else:
        print(" NOTE: Tenant A was not throttled. Check THROTTLE_LIMIT settings.")

    print("\n[Tenant B - Regular Tenant / Isolated Observation]")
    print(f"Status Code Breakdown: {b_statuses}")
    
    num_b_throttled = b_statuses.get(429, 0)
    num_b_success = b_statuses.get(200, 0)

    if b_latencies:
        avg_b = statistics.mean(b_latencies)
        print(f"Latency stats: Min: {min(b_latencies):.2f}ms | Avg: {avg_b:.2f}ms | Max: {max(b_latencies):.2f}ms")
        if avg_base > 0:
            print(f"Latency delta vs baseline: {avg_b - avg_base:+.2f}ms")
    
    if num_b_throttled == 0 and num_b_success == num_tenant_b_reqs:
        print(" SUCCESS: Tenant B was 100% unthrottled (all requests returned 200 OK)!")
    else:
        print(f" FAIL / ISSUE DETECTED: Tenant B received {num_b_throttled} 429 response(s) out of {num_tenant_b_reqs} requests!")

    print("\n" + "=" * 65)

if __name__ == "__main__":
    run_test()
