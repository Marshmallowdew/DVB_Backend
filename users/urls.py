from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView
from .views import (
    RegisterUserView, UserProfileView, UserViewSet, 
    RequestOTPView, VerifyOTPView, LogoutView, MainAdminContactView
)

router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')

urlpatterns = [
    # Пути для стандартной авторизации
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # Регистрация и профиль
    path('register/', RegisterUserView.as_view(), name='register'),
    path('profile/', UserProfileView.as_view(), name='profile'),

    path('auth/request-otp/', RequestOTPView.as_view(), name='request-otp'),
    path('auth/verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),

    path('main-admin-contact/', MainAdminContactView.as_view(), name='main-admin-contact'),

    path('', include(router.urls)),
]
