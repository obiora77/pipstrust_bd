import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_verified', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    # Status
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)  # email verified via OTP

    # Referral
    referral_code = models.CharField(max_length=12, unique=True, blank=True)
    referred_by = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='referrals'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    def save(self, *args, **kwargs):
        if not self.referral_code:
            import random, string
            self.referral_code = ''.join(
                random.choices(string.ascii_uppercase + string.digits, k=10)
            )
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']


class OTP(models.Model):
    OTP_PURPOSE = (
        ('email_verification', 'Email Verification'),
        ('password_reset', 'Password Reset'),
        ('login', 'Login 2FA'),
        ('withdrawal', 'Withdrawal Confirmation'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps')
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=30, choices=OTP_PURPOSE)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'OTP {self.code} for {self.user.email} ({self.purpose})'

    class Meta:
        db_table = 'otps'
        ordering = ['-created_at']


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bitcoin_address = models.CharField(max_length=200, blank=True, null=True)
    ethereum_address = models.CharField(max_length=200, blank=True, null=True)
    usdt_address = models.CharField(max_length=200, blank=True, null=True)
    usdt_erc20_address = models.CharField(max_length=200, blank=True, null=True)
    total_deposited = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_withdrawn = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_earned = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    wallet_balance = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Profile of {self.user.email}'

    class Meta:
        db_table = 'user_profiles'