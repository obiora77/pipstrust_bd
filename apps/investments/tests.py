from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.users.models import User, UserProfile

from .models import Investment, InvestmentPlan, Transaction
from .services import settle_matured_investments


class InvestmentSettlementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='investor@example.com', password='StrongPass123!',
            first_name='Test', last_name='Investor', is_verified=True,
        )
        self.profile = UserProfile.objects.create(user=self.user, wallet_balance=Decimal('50.00'))
        self.plan = InvestmentPlan.objects.create(
            name='Test Plan', min_amount=Decimal('100.00'), max_amount=Decimal('1000.00'),
            roi_percentage=Decimal('20.00'), duration=1, duration_unit='days',
        )
        now = timezone.now()
        self.investment = Investment.objects.create(
            user=self.user, plan=self.plan, amount=Decimal('100.00'),
            roi_percentage=Decimal('20.00'), expected_return=Decimal('120.00'),
            starts_at=now - timedelta(days=2), ends_at=now - timedelta(days=1),
        )

    def test_matured_investment_is_completed_and_credited_once(self):
        settle_matured_investments(user=self.user)
        settle_matured_investments(user=self.user)

        self.investment.refresh_from_db()
        self.profile.refresh_from_db()

        self.assertEqual(self.investment.status, 'completed')
        self.assertEqual(self.investment.progress_percentage, 100)
        self.assertEqual(self.investment.actual_return, Decimal('120.00'))
        self.assertEqual(self.profile.wallet_balance, Decimal('170.00'))
        self.assertEqual(self.profile.total_earned, Decimal('20.00'))
        self.assertEqual(
            Transaction.objects.filter(
                user=self.user, type='roi', reference=str(self.investment.id)
            ).count(),
            1,
        )
