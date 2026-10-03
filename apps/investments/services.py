from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.notifications.models import Notification
from apps.users.models import UserProfile

from .models import Investment, Transaction


def settle_matured_investments(user=None):
    """Atomically complete every matured active investment and credit it once.

    This function is intentionally safe to call from Celery, dashboard reads, and
    investment list reads. Row locks plus the active-status check prevent duplicate
    ROI credits when two requests run at the same time.
    """
    now = timezone.now()
    query = Investment.objects.filter(status='active', ends_at__lte=now)
    if user is not None:
        query = query.filter(user=user)

    investment_ids = list(query.values_list('id', flat=True))
    completed = []

    for investment_id in investment_ids:
        with transaction.atomic():
            investment = (
                Investment.objects.select_for_update()
                .select_related('user', 'plan')
                .filter(id=investment_id, status='active', ends_at__lte=now)
                .first()
            )
            if not investment:
                continue

            profile = UserProfile.objects.select_for_update().get(user=investment.user)
            expected_return = Decimal(investment.expected_return)
            profit = expected_return - Decimal(investment.amount)

            profile.wallet_balance += expected_return
            profile.total_earned += profit
            profile.save(update_fields=['wallet_balance', 'total_earned', 'updated_at'])

            investment.status = 'completed'
            investment.actual_return = expected_return
            investment.completed_at = now
            investment.save(update_fields=['status', 'actual_return', 'completed_at'])

            Transaction.objects.get_or_create(
                user=investment.user,
                type='roi',
                reference=str(investment.id),
                defaults={
                    'amount': expected_return,
                    'status': 'success',
                    'description': f'ROI credited for investment #{str(investment.id)[:8]}',
                },
            )

            Notification.objects.create(
                user=investment.user,
                title='Investment Completed',
                message=(
                    f'Your {investment.plan.name} investment has completed. '
                    f'${expected_return} has been credited to your wallet.'
                ),
                type='success',
            )
            completed.append(investment)

    return completed
