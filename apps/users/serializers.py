from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, OTP, UserProfile


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)
    referral_code = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'phone', 'country', 'password', 'password2', 'referral_code']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        referral_code = validated_data.pop('referral_code', None)
        validated_data.pop('password2')
        referred_by = None
        if referral_code:
            try:
                referred_by = User.objects.get(referral_code=referral_code)
            except User.DoesNotExist:
                pass
        user = User.objects.create_user(**validated_data, referred_by=referred_by)
        UserProfile.objects.create(user=user)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)
    purpose = serializers.ChoiceField(choices=OTP.OTP_PURPOSE)


class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    purpose = serializers.ChoiceField(choices=OTP.OTP_PURPOSE)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password2 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({'new_password': 'Passwords do not match.'})
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password2 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({'new_password': 'Passwords do not match.'})
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            'bitcoin_address', 'ethereum_address', 'usdt_address',
            'bank_name', 'bank_account_number', 'bank_account_name',
            'total_deposited', 'total_withdrawn', 'total_earned', 'wallet_balance',
        ]
        read_only_fields = ['total_deposited', 'total_withdrawn', 'total_earned', 'wallet_balance']


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    referral_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'phone', 'country',
            'avatar', 'is_verified', 'is_staff', 'referral_code', 'referral_count',
            'profile', 'created_at',
        ]
        read_only_fields = ['id', 'email', 'is_verified', 'is_staff', 'referral_code', 'created_at']

    def get_referral_count(self, obj):
        return obj.referrals.count()


class UpdateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'country', 'avatar']
