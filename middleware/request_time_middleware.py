import time
import logging

logger = logging.getLogger(__name__)

class RequestTimingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        duration = (time.perf_counter() - start) * 1000  # milliseconds

        logger.info(
            "%s %s took %.2f ms",
            request.method,
            request.path,
            duration,
        )

        return response