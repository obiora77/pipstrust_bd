from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_notification_email(self, subject, message, recipient_list=None):
    """
    Send email notification.
    If recipient_list is None, sends to the admin email.
    """
    try:
        if recipient_list is None:
            recipient_list = [settings.ADMIN_EMAIL]

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
        )
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task
def process_matured_investments():
    """
    Periodic task: credit ROI for matured investments.
    Run every hour via Celery Beat.
    """
    from apps.investments.models import Investment, Transaction
    from apps.users.models import UserProfile

    now = timezone.now()
    matured = Investment.objects.filter(status='active', ends_at__lte=now)

    for investment in matured:
        try:
            profile = investment.user.profile
            profile.wallet_balance += investment.expected_return
            profile.total_earned += investment.expected_return - investment.amount
            profile.save()

            investment.status = 'completed'
            investment.actual_return = investment.expected_return
            investment.completed_at = now
            investment.save()

            Transaction.objects.create(
                user=investment.user,
                type='roi',
                amount=investment.expected_return,
                status='success',
                description=f'ROI credited for investment #{str(investment.id)[:8]}',
                reference=str(investment.id),
            )

            send_notification_email.delay(
                subject='Investment Matured — ROI Credited',
                message=(
                    f'Hello {investment.user.full_name},\n\n'
                    f'Your investment of ${investment.amount} on the {investment.plan.name} plan '
                    f'has matured. ${investment.expected_return} has been credited to your wallet.\n\n'
                    f'PipsTrust Team'
                ),
                recipient_list=[investment.user.email],
            )
        except Exception as e:
            # Log and continue — don't fail all investments because of one
            print(f'Error processing investment {investment.id}: {e}')


@shared_task
def send_referral_bonus(referrer_id, new_user_email, bonus_amount):
    """Credit referral bonus to referrer's wallet."""
    from apps.users.models import User
    from apps.investments.models import Transaction

    try:
        referrer = User.objects.get(id=referrer_id)
        profile = referrer.profile
        profile.wallet_balance += bonus_amount
        profile.total_earned += bonus_amount
        profile.save()

        Transaction.objects.create(
            user=referrer,
            type='referral_bonus',
            amount=bonus_amount,
            status='success',
            description=f'Referral bonus for inviting {new_user_email}',
        )

        send_notification_email.delay(
            subject='Referral Bonus Credited',
            message=(
                f'Hello {referrer.full_name},\n\n'
                f'You earned a referral bonus of ${bonus_amount} '
                f'for inviting {new_user_email} to RapidTrusts!\n\n'
                f'PipsTrust Team'
            ),
            recipient_list=[referrer.email],
        )
    except Exception as e:
        print(f'Referral bonus error: {e}')
