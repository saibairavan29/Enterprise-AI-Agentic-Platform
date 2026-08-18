from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

User = get_user_model()

class AuthenticationTests(APITestCase):
    """
    Test suite for checking registration, login, token refresh, 
    and profile retrieval/update APIs.
    """
    def setUp(self):
        self.register_url = reverse('auth_register')
        self.login_url = reverse('token_obtain_pair')
        self.profile_url = reverse('user_profile')
        
        # Default test user data
        self.user_data = {
            "username": "testanalyst",
            "email": "analyst@enterprise.ai",
            "password": "securepassword123",
            "password_confirm": "securepassword123",
            "first_name": "Test",
            "last_name": "Analyst",
            "phone_number": "1234567890",
            "role": "analyst"
        }
        
    def test_user_registration(self):
        """
        Verify that new users can self-register with standard parameters.
        """
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['username'], "testanalyst")
        self.assertEqual(response.data['data']['role'], "analyst")

    def test_user_login_and_token_generation(self):
        """
        Verify that valid credentials return JWT access & refresh tokens.
        """
        # Register first
        self.client.post(self.register_url, self.user_data, format='json')
        
        # Login
        login_data = {
            "username": "testanalyst",
            "password": "securepassword123"
        }
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data['data'])
        self.assertIn('refresh', response.data['data'])
        self.assertEqual(response.data['data']['user']['role'], "analyst")

    def test_profile_retrieval_requires_auth(self):
        """
        Verify that unauthenticated requests to profile endpoints are denied.
        """
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_retrieval_and_update_with_jwt(self):
        """
        Verify that authenticated users can fetch and update profile fields.
        """
        # Register
        self.client.post(self.register_url, self.user_data, format='json')
        
        # Login to obtain access token
        login_data = {
            "username": "testanalyst",
            "password": "securepassword123"
        }
        login_response = self.client.post(self.login_url, login_data, format='json')
        access_token = login_response.data['data']['access']
        
        # Authenticate requests
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Get Profile
        profile_response = self.client.get(self.profile_url)
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_response.data['data']['username'], "testanalyst")
        
        # Update Profile
        update_data = {
            "first_name": "UpdatedName",
            "phone_number": "0987654321"
        }
        update_response = self.client.put(self.profile_url, update_data, format='json')
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data['data']['first_name'], "UpdatedName")
        self.assertEqual(update_response.data['data']['phone_number'], "0987654321")
