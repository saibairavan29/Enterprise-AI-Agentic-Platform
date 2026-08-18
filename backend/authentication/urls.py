from django.urls import path
from .views import CustomTokenObtainPairView, CustomTokenRefreshView, RegistrationView, UserProfileView

urlpatterns = [
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('login/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('register/', RegistrationView.as_view(), name='auth_register'),
    path('profile/', UserProfileView.as_view(), name='user_profile'),
]
