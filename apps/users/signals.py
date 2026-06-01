from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, UserProfile


@receiver(post_save, sender=User)
def handle_new_user(sender, instance, created, **kwargs):
    """
    After user is verified for the first time, credit referral bonus to referrer.
    Profile creation is handled in RegisterSerializer.
    """
    pass


@receiver(post_save, sender=User)
def credit_referral_on_verification(sender, instance, **kwargs):
    """
    When a user's is_verified changes to True and they have a referrer,
    trigger the referral bonus task.
    """
    if instance.is_verified and instance.referred_by:
        # Only fire once — check if referral bonus already given
        from apps.investments.models import Transaction
        already_given = Transaction.objects.filter(
            user=instance.referred_by,
            type='referral_bonus',
            description__icontains=instance.email,
        ).exists()

        if not already_given:
            from apps.notifications.tasks import send_referral_bonus
            REFERRAL_BONUS = 5.00  # $5 referral bonus — adjust as needed
            send_referral_bonus.delay(
                referrer_id=str(instance.referred_by.id),
                new_user_email=instance.email,
                bonus_amount=REFERRAL_BONUS,
            )
