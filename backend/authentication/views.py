import logging
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    CustomTokenObtainPairSerializer, 
    RegistrationSerializer, 
    UserProfileSerializer
)

User = get_user_model()
logger = logging.getLogger('enterprise')

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Login view returning JWT access/refresh tokens and user details
    wrapped in standard success response payload.
    """
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            response.data = {
                "success": True,
                "status_code": 200,
                "message": "Credentials verified and token issued.",
                "data": response.data,
                "errors": [],
                "timestamp": timezone.now().isoformat()
            }
        return response


class CustomTokenRefreshView(TokenRefreshView):
    """
    Token refresh view returning new access token wrapped in standard response payload.
    """
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            response.data = {
                "success": True,
                "status_code": 200,
                "message": "Access token rotated successfully.",
                "data": response.data,
                "errors": [],
                "timestamp": timezone.now().isoformat()
            }
        return response


class RegistrationView(APIView):
    """
    Self-registration view allowing new user onboarding.
    Requires no authentication permission.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        logger.info("Sign-up attempt received.")
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        logger.info(f"User registration successful: {user.username}")
        
        return Response({
            "success": True,
            "status_code": status.HTTP_201_CREATED,
            "message": "User registered successfully.",
            "data": {
                "username": user.username,
                "email": user.email,
                "role": user.role
            },
            "errors": [],
            "timestamp": timezone.now().isoformat()
        }, status=status.HTTP_201_CREATED)


class UserProfileView(APIView):
    """
    Retrieve or update the logged-in user's profile metadata.
    Requires JWT authentication.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response({
            "success": True,
            "status_code": status.HTTP_200_OK,
            "message": "Profile retrieved successfully.",
            "data": serializer.data,
            "errors": [],
            "timestamp": timezone.now().isoformat()
        }, status=status.HTTP_200_OK)

    def put(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info(f"Profile updated for user: {request.user.username}")
        
        return Response({
            "success": True,
            "status_code": status.HTTP_200_OK,
            "message": "Profile updated successfully.",
            "data": serializer.data,
            "errors": [],
            "timestamp": timezone.now().isoformat()
        }, status=status.HTTP_200_OK)
