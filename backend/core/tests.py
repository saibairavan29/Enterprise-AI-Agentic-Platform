from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

class HealthCheckTests(APITestCase):
    """
    Test suite for testing the health check endpoint.
    """
    def setUp(self):
        self.health_url = reverse('health_check')

    def test_health_check_endpoint(self):
        """
        Verify that the health check endpoint responds with a successful status
        and structured JSON payload.
        """
        response = self.client.get(self.health_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        data = response.data['data']
        self.assertIn('application', data)
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['version'], '1.0.0')
        self.assertEqual(data['database_connection'], 'healthy')
        self.assertIn('timestamp', response.data)
        self.assertIn('environment', data)
