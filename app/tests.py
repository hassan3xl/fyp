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
    def test_throttle_limit_from_settings_redirects_and_bypasses(self):
        request = Mock()
        request.path = "/dashboard/"
        request.tenant_id = "tenant-1"
        request.META = {'HTTP_REFERER': '/dashboard/'}
        request.headers = {}
        
        # Mock session to support bypass flag
        session_data = {}
        request.session = session_data

        # Mock Django messages
        import django.contrib.messages
        django.contrib.messages.error = Mock()

        # Request 1: OK
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

        # Request 2: OK
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

        # Request 3: Exceeded (limit is 2) - should redirect back
        response = self.middleware(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/dashboard/')
        self.assertTrue(session_data.get('throttled_bypass'))
        django.contrib.messages.error.assert_called_once()

        # Request 4: Bypass should kick in on next request
        self.get_response.reset_mock()
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(session_data.get('throttled_bypass'))
        self.get_response.assert_called_once_with(request)

    @override_settings(THROTTLE_LIMIT=2)
    def test_throttle_ajax_returns_429(self):
        request = Mock()
        request.path = "/dashboard/"
        request.tenant_id = "tenant-ajax"
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
        self.assertIn('application/json', response['Content-Type'])

    @override_settings(THROTTLE_LIMIT=2)
    def test_sliding_window_behavior(self):
        from unittest.mock import patch
        
        request = Mock()
        request.path = "/dashboard/"
        request.tenant_id = "tenant-sliding"
        request.META = {'HTTP_REFERER': '/dashboard/'}
        request.headers = {}
        request.session = {}
        
        with patch('time.time') as mock_time:
            # First request at t = 100.0 -> OK
            mock_time.return_value = 100.0
            response = self.middleware(request)
            self.assertEqual(response.status_code, 200)

            # Second request at t = 130.0 -> OK
            mock_time.return_value = 130.0
            response = self.middleware(request)
            self.assertEqual(response.status_code, 200)

            # Third request at t = 150.0 -> Blocked (limit is 2)
            mock_time.return_value = 150.0
            response = self.middleware(request)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response['Retry-After'], '10') # 100.0 + 60 - 150.0 = 10

            # Consume bypass from session to test the next request under throttling limit
            if request.session.get('throttled_bypass'):
                request.session.pop('throttled_bypass', None)

            # Fourth request at t = 161.0 -> OK (first request at t=100.0 has slid out)
            mock_time.return_value = 161.0
            response = self.middleware(request)
            self.assertEqual(response.status_code, 200)



