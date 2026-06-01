import random
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from .models import OTP


def generate_otp_code():
    """Generate a 6-digit OTP code."""
    return str(random.randint(100000, 999999))


def create_otp(user, purpose):
    """Invalidate old OTPs and create a new one."""
    OTP.objects.filter(user=user, purpose=purpose, is_used=False).update(is_used=True)
    expiry = timezone.now() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
    code = generate_otp_code()
    otp = OTP.objects.create(user=user, code=code, purpose=purpose, expires_at=expiry)
    return otp


def verify_otp(user, code, purpose):
    """
    Verify OTP. Returns (True, None) on success or (False, error_message).
    """
    try:
        otp = OTP.objects.get(
            user=user, code=code, purpose=purpose, is_used=False
        )
    except OTP.DoesNotExist:
        return False, 'Invalid OTP code.'

    if otp.expires_at < timezone.now():
        return False, 'OTP has expired. Please request a new one.'

    otp.is_used = True
    otp.save()
    return True, None


def send_otp_email(user, otp):
    """Send OTP email to the user."""
    purpose_labels = {
        'email_verification': 'Email Verification',
        'password_reset': 'Password Reset',
        'login': 'Login Verification',
        'withdrawal': 'Withdrawal Confirmation',
    }

    subject_map = {
        'email_verification': 'Verify Your Email - PipsTrust',
        'password_reset': 'Password Reset OTP - PipsTrust',
        'login': 'Login Verification Code - PipsTrust',
        'withdrawal': 'Withdrawal Confirmation OTP - PipsTrust',
    }

    context = {
        'user': user,
        'otp_code': otp.code,
        'purpose_label': purpose_labels.get(otp.purpose, 'Verification'),
        'expiry_minutes': settings.OTP_EXPIRY_MINUTES,
        'frontend_url': settings.FRONTEND_URL,
    }

    subject = subject_map.get(otp.purpose, 'OTP Code - PipsTrust')

    # Plain text fallback
    text_content = (
        f"Hello {user.full_name},\n\n"
        f"Your OTP for {context['purpose_label']} is: {otp.code}\n"
        f"This code expires in {settings.OTP_EXPIRY_MINUTES} minutes.\n\n"
        f"If you did not request this, please ignore this email.\n\n"
        f"PipsTrust Team"
    )

    try:
        html_content = render_to_string('emails/otp.html', context)
    except Exception:
        html_content = None

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )

    if html_content:
        msg.attach_alternative(html_content, "text/html")

    msg.send(fail_silently=False)
