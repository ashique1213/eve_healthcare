from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import RegisterView, CustomTokenObtainPairView, UserProfileView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('signup/', RegisterView.as_view(), name='auth-signup'),  # Alias for register
    path('login/', CustomTokenObtainPairView.as_view(), name='auth-login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='auth-token-refresh'),
    path('profile/', UserProfileView.as_view(), name='auth-profile'),
]
