from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from apps.users.models import User, UserProfile

from .models import Withdrawal


class WithdrawalFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='withdraw@example.com', password='StrongPass123!',
            first_name='Test', last_name='User', is_verified=True,
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            wallet_balance=Decimal('500.00'),
            bitcoin_address='bc1-test-address',
            ethereum_address='0x-test-eth',
            usdt_address='T-test-trc20',
            usdt_erc20_address='0x-test-usdt',
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    @patch('apps.withdrawals.views.send_otp_email')
    @patch('apps.withdrawals.views.create_otp', return_value=object())
    def test_request_holds_funds_and_cancel_refunds_once(self, _create_otp, _send_otp):
        response = self.client.post('/api/withdrawals/request/', {
            'amount': '125.00', 'method': 'bitcoin',
        }, format='json')
        self.assertEqual(response.status_code, 201)

        withdrawal = Withdrawal.objects.get(id=response.data['data']['withdrawal_id'])
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.wallet_balance, Decimal('375.00'))
        self.assertEqual(withdrawal.payout_address, 'bc1-test-address')

        cancel = self.client.post(f'/api/withdrawals/{withdrawal.id}/cancel/', {}, format='json')
        self.assertEqual(cancel.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.wallet_balance, Decimal('500.00'))

        second_cancel = self.client.post(f'/api/withdrawals/{withdrawal.id}/cancel/', {}, format='json')
        self.assertEqual(second_cancel.status_code, 404)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.wallet_balance, Decimal('500.00'))

    @patch('apps.withdrawals.views.send_otp_email')
    @patch('apps.withdrawals.views.create_otp', return_value=object())
    def test_usdt_erc20_method_uses_erc20_address(self, _create_otp, _send_otp):
        response = self.client.post('/api/withdrawals/request/', {
            'amount': '50.00', 'method': 'usdt2',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        withdrawal = Withdrawal.objects.get(id=response.data['data']['withdrawal_id'])
        self.assertEqual(withdrawal.payout_address, '0x-test-usdt')
