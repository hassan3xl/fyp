from django.test import TestCase, override_settings
from django.core.cache import cache
from django.http import HttpResponse
from middleware.throttle_middleware import ThrottleMiddleware
from unittest.mock import Mock

class ThrottleMiddlewareTests(TestCase):
    def setUp(self):
        cache.clear()
        self.get_response = Mock(return_value=HttpResponse("OK"))
        self.middleware = ThrottleMiddleware(self.get_response)

    def test_throttle_exempt_paths(self):
        request = Mock(path="/static/js/app.js")
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)
        self.get_response.assert_called_once_with(request)

    @override_settings(THROTTLE_LIMIT=2)
    def test_throttle_limit_from_settings(self):
        request = Mock()
        request.path = "/dashboard/"
        request.tenant_id = "tenant-1"
        request.META = {}
        request.headers = {'x-requested-with': 'XMLHttpRequest'}
        request.session = {}

        # Request 1: OK
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

        # Request 2: OK
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

        # Request 3: Exceeded (limit is 2)
        response = self.middleware(request)
        self.assertEqual(response.status_code, 429)

    @override_settings(THROTTLE_LIMIT=2)
    def test_throttle_by_ip_fallback(self):
        request = Mock()
        request.path = "/dashboard/"
        request.tenant_id = None
        request.META = {'REMOTE_ADDR': '192.168.1.1'}
        request.headers = {'x-requested-with': 'XMLHttpRequest'}
        request.session = {}

        # Request 1: OK
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

        # Request 2: OK
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

        # Request 3: Exceeded (limit is 2)
        response = self.middleware(request)
        self.assertEqual(response.status_code, 429)


