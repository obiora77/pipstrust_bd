from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import authenticate
from drf_spectacular.utils import extend_schema, OpenApiExample
from django.utils import timezone

from .models import User
from .serializers import (
    RegisterSerializer, LoginSerializer, OTPVerifySerializer,
    ResendOTPSerializer, PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer, ChangePasswordSerializer,
    UserSerializer, UpdateProfileSerializer, UserProfileSerializer,
)
from .otp_utils import create_otp, verify_otp, send_otp_email

def api_response(data=None, message='', status_str='success', errors=None, http_status=200):
    return Response(
        {
            'status': status_str,
            'message': message,
            'data': data,
            'errors': errors,
            'meta': {'timestamp': timezone.now().isoformat(), 'version': '1.0.1'}
        }
    )

class OTPRateThrottle(AnonRateThrottle):
    rate = '5/hour'
    scope = 'otp'

# ─── Registration ─────────────────────────────────────────────────────────────
@extend_schema(tags=['Auth'])
class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=RegisterSerializer,
        responses={201: {'description': 'User registered. OTP sent to email.'}},
        summary='Register a new user',
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                message='Validation failed',
                status_str='error',
                errors=serializer.errors, 
                http_status=400,
            )
        user = serializer.save()
        otp = create_otp(user, 'email_verification')
        send_otp_email(user, otp)
        return api_response(
            data={'email': user.email},
            message='Registration successful. Please check your email to verify your account.',
            http_status=201
        )


# ─── OTP Verification ─────────────────────────────────────────────────────────
@extend_schema(tags=['Auth'])
class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPRateThrottle]

    @extend_schema(
        request=OTPVerifySerializer,
        summary='Verify email using OTP',
    )
    def post(self, request):
        serializer = OTPVerifySerializer(data={**request.data, 'purpose': 'email_verification'})
        if not serializer.is_valid():
            return api_response(message='Validation failed.', status_str='error', errors=serializer.errors, http_status=400)
        try:
            user = User.objects.get(email=serializer.validated_data['email'])
        except User.DoesNotExist:
            return api_response(message='User not found.', status_str='error', http_status=404)

        success, error = verify_otp(user, serializer.validated_data['code'], 'email_verification')
        if not success:
            return api_response(message=error, status_str='error', http_status=400)

        user.is_verified = True
        user.save()
        tokens = _get_tokens(user)
        return api_response(
            data={**tokens,'user': UserSerializer(user).data},
            message='Email verified successfully.',
        )


# ─── Resend OTP ───────────────────────────────────────────────────────────────
@extend_schema(tags=['Auth'])
class ResendOTPView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPRateThrottle]

    @extend_schema(request=ResendOTPSerializer, summary='Resend OTP')
    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(message='Validation failed.', status_str='error', errors=serializer.errors, http_status=400)
        
        try:
            user = User.objects.get(email=serializer.validated_data['email'])
        except User.DoesNotExist:
            return api_response(message='User not found.', status_str='error', http_status=404)

        otp = create_otp(user, serializer.validated_data['purpose'])
        send_otp_email(user, otp)
        return api_response(message='OTP sent successfully. Check your email.')


# ─── Login ────────────────────────────────────────────────────────────────────
@extend_schema(tags=['Auth'])
class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=LoginSerializer, summary='Login with email and password')
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(message='Validation failed.', status_str='error', errors=serializer.errors, http_status=400)
        
        user = authenticate(
            request,
            username=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
        )
        if not user:
            return api_response(message='Invalid email or password.', status_str='error', http_status=401)
        if not user.is_active:
            return api_response(message='Account is disabled.', status_str='error', http_status=403)
        if not user.is_verified:
            # Re-send verification OTP
            otp = create_otp(user, 'email_verification')
            send_otp_email(user, otp)
            return api_response(
                message='Email not verified. A new OTP has been sent to your email.',
                status_str='error',
                errors={'requires_verification': True, 'email': user.email},
                http_status=403,
            )

        tokens = _get_tokens(user)
        return api_response(
            data={**tokens, 'user': UserSerializer(user).data},
            message='Login successful.',
        )


# ─── Logout ───────────────────────────────────────────────────────────────────
@extend_schema(tags=['Auth'])
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary='Logout (blacklist refresh token)')
    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return api_response(message='Refresh token required.', status_str='error', http_status=400)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return api_response(message='Invalid token.', status_str='error', http_status=400)
        return api_response(message='Logged out successfully.')


# ─── Password Reset ───────────────────────────────────────────────────────────
@extend_schema(tags=['Auth'])
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPRateThrottle]

    @extend_schema(request=PasswordResetRequestSerializer, summary='Request password reset OTP')
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(message='Validation failed.', status_str='error', errors=serializer.errors, http_status=400)
        
        try:
            user = User.objects.get(email=serializer.validated_data['email'])
            otp = create_otp(user, 'password_reset')
            send_otp_email(user, otp)
        except User.DoesNotExist:
            pass  # Don't reveal if email exists
        return api_response(message='If an account exists with this email, a reset OTP has been sent.')


@extend_schema(tags=['Auth'])
class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=PasswordResetConfirmSerializer, summary='Confirm password reset with OTP')
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(message='Validation failed.', status_str='error', errors=serializer.errors, http_status=400)
        
        try:
            user = User.objects.get(email=serializer.validated_data['email'])
        except User.DoesNotExist:
            return api_response(message='User not found.', status_str='error', http_status=404)

        success, error = verify_otp(user, serializer.validated_data['code'], 'password_reset')
        if not success:
            return api_response(message=error, status_str='error', http_status=400)

        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return api_response(message='Password reset successfully. You can now login.')


# ─── Change Password ──────────────────────────────────────────────────────────
@extend_schema(tags=['Auth'])
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=ChangePasswordSerializer, summary='Change password (authenticated)')
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(message='Validation failed.', status_str='error', errors=serializer.errors, http_status=400)
        
        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return api_response(message='Old password is incorrect.', status_str='error', http_status=400)
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return api_response(message='Password changed successfully.')


# ─── Profile ──────────────────────────────────────────────────────────────────
@extend_schema(tags=['Profile'])
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary='Get current user profile')
    def get(self, request):
        return api_response(data=UserSerializer(request.user).data)

    @extend_schema(request=UpdateProfileSerializer, summary='Update profile')
    def patch(self, request):
        serializer = UpdateProfileSerializer(request.user, data=request.data, partial=True)
        if not serializer.is_valid():
            return api_response(message='Validation failed.', status_str='error', errors=serializer.errors, http_status=400)
        serializer.save()
        return api_response(data=UserSerializer(request.user).data, message='Profile updated.')


@extend_schema(tags=['Profile'])
class UpdateWalletAddressView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=UserProfileSerializer, summary='Update wallet / bank info')
    def patch(self, request):
        profile = request.user.profile
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        if not serializer.is_valid():
            return api_response(message='Validation failed.', status_str='error', errors=serializer.errors, http_status=400)
        serializer.save()
        return api_response(data=serializer.data, message='Wallet info updated.')


# ─── Helper ───────────────────────────────────────────────────────────────────
def _get_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }
