import os
import time
import logging
import threading
import urllib.request
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def ping_view(request):
    """
    Lightweight health-check / ping endpoint.
    Returns HTTP 200 to confirm backend is awake.
    """
    return JsonResponse({
        "status": "healthy",
        "service": "multi-tenant-inventory",
        "message": "pong"
    })


def start_render_keep_alive():
    """
    Background daemon thread to periodically ping the Render service URL
    (every 13 minutes) to prevent Render free-tier instances from spinning down/sleeping.
    """
    render_url = (
        os.environ.get("RENDER_EXTERNAL_URL")
        or os.environ.get("RENDER_URL")
        or os.environ.get("PING_URL")
    )
    if not render_url:
        return

    ping_endpoint = render_url.rstrip("/") + "/ping/"

    def keep_alive_worker():
        # Initial delay before starting keep-alive loop
        time.sleep(30)
        while True:
            try:
                req = urllib.request.Request(
                    ping_endpoint,
                    headers={"User-Agent": "Render-KeepAlive-Bot/1.0"}
                )
                with urllib.request.urlopen(req, timeout=15) as response:
                    logger.info("Keep-alive ping sent to %s (Status: %s)", ping_endpoint, response.status)
            except Exception as exc:
                logger.warning("Keep-alive ping failed: %s", exc)
            # Sleep for 13 minutes (Render free tier spins down after 15 mins of inactivity)
            time.sleep(13 * 60)

    thread = threading.Thread(target=keep_alive_worker, daemon=True, name="RenderKeepAliveWorker")
    thread.start()


# Automatically start keep-alive worker in production / Render environments
if os.environ.get("RENDER") or os.environ.get("RENDER_EXTERNAL_URL") or os.environ.get("PING_URL"):
    start_render_keep_alive()


urlpatterns = [
    path('ping/', ping_view, name='ping'),
    path('admin/', admin.site.urls),
    path('', include('app.urls.auth_urls')),
    path('<slug:tenant_slug>/', include('app.urls')),
]
