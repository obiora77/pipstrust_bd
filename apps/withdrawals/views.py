from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction as db_transaction
from drf_spectacular.utils import extend_schema

from .models import Withdrawal
from .serializers import WithdrawalRequestSerializer, WithdrawalSerializer, OTPWithdrawalVerifySerializer
from apps.users.otp_utils import create_otp, verify_otp, send_otp_email
from apps.investments.models import Transaction
from apps.notifications.email_utils import send_html_email
from apps.users.views import api_response


@extend_schema(tags=['Withdrawals'])
class WithdrawalRequestView(APIView):
    """
    Step 1: User submits a withdrawal request.
    System deducts from wallet immediately (held), sends OTP for confirmation.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(request=WithdrawalRequestSerializer, summary='Request a withdrawal (sends OTP)')
    def post(self, request):
        serializer = WithdrawalRequestSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return api_response(message='Validation failed.', status_str='error', errors=serializer.errors, http_status=400)

        user = request.user
        profile = user.profile
        amount = serializer.validated_data['amount']
        method = serializer.validated_data['method']

        with db_transaction.atomic():
            extra = {}
            if method == 'bitcoin':
                extra['payout_address'] = profile.bitcoin_address
            elif method == 'ethereum':
                extra['payout_address'] = profile.ethereum_address
            elif method == 'usdt':
                extra['payout_address'] = profile.usdt_address

            withdrawal = Withdrawal.objects.create(
                user=user, amount=amount, method=method, **extra
            )

            profile.wallet_balance -= amount
            profile.save()

            Transaction.objects.create(
                user=user,
                type='withdrawal',
                amount=amount,
                status='pending',
                description=f'Withdrawal via {withdrawal.get_method_display()}',
                reference=str(withdrawal.id),
            )

        otp = create_otp(user, 'withdrawal')
        send_otp_email(user, otp)

        return api_response(
            data={'withdrawal_id': str(withdrawal.id)},
            message='Withdrawal request created. Please confirm with the OTP sent to your email.',
            http_status=201,
        )


@extend_schema(tags=['Withdrawals'])
class WithdrawalOTPVerifyView(APIView):
    """
    Step 2: User confirms withdrawal using OTP.
    Moves status to otp_verified — admin processes it manually.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(request=OTPWithdrawalVerifySerializer, summary='Confirm withdrawal with OTP')
    def post(self, request):
        serializer = OTPWithdrawalVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(message='Validation failed.', status_str='error', errors=serializer.errors, http_status=400)

        try:
            withdrawal = Withdrawal.objects.get(
                id=serializer.validated_data['withdrawal_id'],
                user=request.user,
                status='pending',
            )
        except Withdrawal.DoesNotExist:
            return api_response(message='Withdrawal not found or already processed.', status_str='error', http_status=404)

        success, error = verify_otp(request.user, serializer.validated_data['code'], 'withdrawal')
        if not success:
            return api_response(message=error, status_str='error', http_status=400)

        withdrawal.status = 'otp_verified'
        withdrawal.save()

        send_html_email(
                subject='Withdrawal Confirmed by User',
                template_name='broadcast',
                context={'user_name': 'User', 'message': f'{request.user.email} confirmed withdrawal of ${withdrawal.amount} via {withdrawal.method}.'},
                recipient_list=None,
            )

        return api_response(message='Withdrawal confirmed. It will be processed shortly.')


@extend_schema(tags=['Withdrawals'])
class WithdrawalListView(generics.ListAPIView):
    serializer_class = WithdrawalSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'method']
    ordering_fields = ['created_at', 'amount']

    def get_queryset(self):
        return Withdrawal.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return api_response(data=serializer.data)


@extend_schema(tags=['Withdrawals'])
class WithdrawalDetailView(generics.RetrieveAPIView):
    serializer_class = WithdrawalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Withdrawal.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return api_response(data=serializer.data)


@extend_schema(tags=['Withdrawals'])
class WithdrawalCancelView(APIView):
    """Cancel a pending (not yet OTP verified) withdrawal and refund wallet."""
    permission_classes = [IsAuthenticated]

    @extend_schema(summary='Cancel a pending withdrawal')
    def post(self, request, pk):
        try:
            withdrawal = Withdrawal.objects.get(id=pk, user=request.user, status='pending')
        except Withdrawal.DoesNotExist:
            return api_response(message='Withdrawal not found or cannot be cancelled.', status_str='error', http_status=404)

        with db_transaction.atomic():
            withdrawal.status = 'rejected'
            withdrawal.admin_note = 'Cancelled by user.'
            withdrawal.save()

            profile = request.user.profile
            profile.wallet_balance += withdrawal.amount
            profile.save()

            Transaction.objects.filter(
                reference=str(withdrawal.id), type='withdrawal'
            ).update(status='failed')

        return api_response(message='Withdrawal cancelled and amount refunded to your wallet.')