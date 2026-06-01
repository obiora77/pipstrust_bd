from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, LoginView, LogoutView,
    VerifyEmailView, ResendOTPView,
    PasswordResetRequestView, PasswordResetConfirmView, ChangePasswordView,
    MeView, UpdateWalletAddressView,
)

urlpatterns = [
    # Auth
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),

    # OTP
    path('otp/verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('otp/resend/', ResendOTPView.as_view(), name='resend-otp'),

    # Password
    path('password/reset/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password/reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('password/change/', ChangePasswordView.as_view(), name='change-password'),

    # Profile
    path('me/', MeView.as_view(), name='me'),
    path('me/wallet/', UpdateWalletAddressView.as_view(), name='update-wallet'),
]
