from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction as db_transaction
from django.db.models import Sum, Count, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema

from .permissions import IsAdminUser
from .serializers import (
    AdminUserSerializer, AdminUserUpdateSerializer,
    AdminDepositSerializer, AdminDepositActionSerializer,
    AdminWithdrawalSerializer, AdminWithdrawalActionSerializer,
    AdminInvestmentPlanSerializer, AdminPlatformStatsSerializer,
    AdminBroadcastSerializer, AdminCreditWalletSerializer,
)
from apps.users.models import User, UserProfile
from apps.investments.models import InvestmentPlan, Deposit, Investment, Transaction
from apps.investments.services import settle_matured_investments
from apps.withdrawals.models import Withdrawal
from apps.notifications.models import Notification
from apps.notifications.email_utils import send_html_email
from apps.users.views import api_response


# ─── Platform Stats ───────────────────────────────────────────────────────────
@extend_schema(tags=['Admin — Stats'])
class AdminPlatformStatsView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(responses=AdminPlatformStatsSerializer, summary='Get platform-wide statistics')
    def get(self, request):
        settle_matured_investments()
        total_deposits = Deposit.objects.filter(status='confirmed').aggregate(
            total=Sum('amount')
        )['total'] or 0

        total_withdrawals = Withdrawal.objects.filter(status='completed').aggregate(
            total=Sum('amount')
        )['total'] or 0

        from apps.users.models import UserProfile
        total_platform_balance = UserProfile.objects.aggregate(
            total=Sum('wallet_balance')
        )['total'] or 0

        data = {
            'total_users': User.objects.count(),
            'verified_users': User.objects.filter(is_verified=True).count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'total_deposits': total_deposits,
            'total_withdrawals': total_withdrawals,
            'total_active_investments': Investment.objects.filter(status='active').count(),
            'total_completed_investments': Investment.objects.filter(status='completed').count(),
            'pending_deposits': Deposit.objects.filter(status='pending').count(),
            'pending_withdrawals': Withdrawal.objects.filter(status__in=['pending', 'otp_verified']).count(),
            'total_platform_balance': total_platform_balance,
        }
        return api_response(data=AdminPlatformStatsSerializer(data).data)


# ─── User Management ──────────────────────────────────────────────────────────
@extend_schema(tags=['Admin — Users'])
class AdminUserListView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminUserSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active', 'is_verified', 'is_staff', 'country']
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    ordering_fields = ['created_at', 'email']

    def get_queryset(self):
        return User.objects.select_related('profile').all()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return api_response(data=serializer.data)


@extend_schema(tags=['Admin — Users'])
class AdminUserDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAdminUser]
    queryset = User.objects.select_related('profile').all()

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return AdminUserUpdateSerializer
        return AdminUserSerializer

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)


@extend_schema(tags=['Admin — Users'])
class AdminToggleUserStatusView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(summary='Toggle user active status (ban/unban)')
    def post(self, request, pk):
        try:
            user = User.objects.get(id=pk)
        except User.DoesNotExist:
            return api_response(message='User not found.', status_str='error', http_status=404)

        user.is_active = not user.is_active
        user.save()
        action = 'activated' if user.is_active else 'deactivated'
        return api_response(
            data={'is_active': user.is_active},
            message=f'User {action} successfully.',
        )


@extend_schema(tags=['Admin — Users'])
class AdminCreditWalletView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(request=AdminCreditWalletSerializer, summary='Manually credit a user wallet')
    def post(self, request):
        serializer = AdminCreditWalletSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(message='Validation failed.', status_str='error', errors=serializer.errors, http_status=400)

        try:
            user = User.objects.get(id=serializer.validated_data['user_id'])
        except User.DoesNotExist:
            return api_response(message='User not found.', status_str='error', http_status=404)

        amount = serializer.validated_data['amount']
        description = serializer.validated_data['description']

        with db_transaction.atomic():
            profile = user.profile
            profile.wallet_balance += amount
            profile.total_earned += amount
            profile.save()

            Transaction.objects.create(
                user=user,
                type='roi',
                amount=amount,
                status='success',
                description=description,
            )

            Notification.objects.create(
                user=user,
                title='Wallet Credited',
                message=f'${amount} has been credited to your wallet. {description}',
                type='success',
            )

        send_html_email(
                subject='Wallet Credited',
                template_name='broadcast',
                context={'user_name': 'User', 'message': f'Hello {user.full_name},\n\n${amount} has been credited to your wallet.\n\nPipsTrust Team'},
                recipient_list=[user.email],
            )

        return api_response(message=f'${amount} credited to {user.email} successfully.')


# ─── Deposit Management ───────────────────────────────────────────────────────
@extend_schema(tags=['Admin — Deposits'])
class AdminDepositListView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminDepositSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'payment_method']
    search_fields = ['user__email', 'transaction_hash']
    ordering_fields = ['created_at', 'amount']

    def get_queryset(self):
        return Deposit.objects.select_related('user').all()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return api_response(data=serializer.data)


@extend_schema(tags=['Admin — Deposits'])
class AdminDepositDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminDepositSerializer
    queryset = Deposit.objects.select_related('user').all()


@extend_schema(tags=['Admin — Deposits'])
class AdminDepositActionView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(request=AdminDepositActionSerializer, summary='Approve or reject a deposit')
    def post(self, request, pk):
        serializer = AdminDepositActionSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(message='Validation failed.', status_str='error', errors=serializer.errors, http_status=400)

        action = serializer.validated_data['action']
        admin_note = serializer.validated_data.get('admin_note', '')

        with db_transaction.atomic():
            deposit = (Deposit.objects.select_for_update().select_related('user').filter(id=pk, status='pending').first())
            if not deposit:
                return api_response(message='Deposit not found or already processed.', status_str='error', http_status=404)
            
            if action == 'approve':
                deposit.status = 'confirmed'
                deposit.confirmed_at = timezone.now()
                deposit.admin_note = admin_note
                deposit.save()

                profile = UserProfile.objects.select_for_update().get(user=deposit.user)
                profile.wallet_balance += deposit.amount
                profile.total_deposited += deposit.amount
                profile.save(update_fields=['wallet_balance', 'total_deposit', 'updated_at'])

                Transaction.objects.filter(
                    reference=str(deposit.id), type='deposit'
                ).update(status='success')

                Notification.objects.create(
                    user=deposit.user,
                    title='Deposit Confirmed',
                    message=f'Your deposit of ${deposit.amount} has been confirmed.',
                    type='success',
                )

                send_html_email(
                subject='Deposit Confirmed',
                template_name='broadcast',
                context={'user_name': 'User', 'message': f'Your deposit of ${deposit.amount} has been approved and added to your wallet.'},
                recipient_list=[deposit.user.email],
            )
                return api_response(message='Deposit approved successfully.')

            else:  # reject
                deposit.status = 'rejected'
                deposit.admin_note = admin_note
                deposit.save()

                Transaction.objects.filter(
                    reference=str(deposit.id), type='deposit'
                ).update(status='failed')

                Notification.objects.create(
                    user=deposit.user,
                    title='Deposit Rejected',
                    message=f'Your deposit of ${deposit.amount} was rejected. {admin_note}',
                    type='error',
                )

                send_html_email(
                subject='Deposit Rejected',
                template_name='broadcast',
                context={'user_name': 'User', 'message': f'Your deposit of ${deposit.amount} was rejected. Reason: {admin_note}'},
                recipient_list=[deposit.user.email],
            )
                return api_response(message='Deposit rejected.')


# ─── Withdrawal Management ────────────────────────────────────────────────────
@extend_schema(tags=['Admin — Withdrawals'])
class AdminWithdrawalListView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminWithdrawalSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'method']
    search_fields = ['user__email']
    ordering_fields = ['created_at', 'amount']

    def get_queryset(self):
        return Withdrawal.objects.select_related('user').all()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return api_response(data=serializer.data)


@extend_schema(tags=['Admin — Withdrawals'])
class AdminWithdrawalDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminWithdrawalSerializer
    queryset = Withdrawal.objects.select_related('user').all()


@extend_schema(tags=['Admin — Withdrawals'])
class AdminWithdrawalActionView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(request=AdminWithdrawalActionSerializer, summary='Approve or reject a withdrawal')
    def post(self, request, pk):
        serializer = AdminWithdrawalActionSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(message='Validation failed.', status_str='error', errors=serializer.errors, http_status=400)

        action = serializer.validated_data['action']
        admin_note = serializer.validated_data.get('admin_note', '')

        with db_transaction.atomic():
            withdrawal = (
                Withdrawal.objects.select_for_update().select_related('user').filter(
                    id=pk, status__in=['otp_verified', 'processing']
                ).first()
            )
            if not withdrawal:
                return api_response(message='Withdrawal not found or not ready for action', status_str='error', http_status=404)
            
            if action == 'approve':
                withdrawal.status = 'completed'
                withdrawal.admin_note = admin_note
                withdrawal.processed_at = timezone.now()
                withdrawal.save()

                profile = UserProfile.objects.select_for_update().get(user=withdrawal.user)
                profile.total_withdrawn += withdrawal.amount
                profile.save(update_fields=['total_withdrawn', 'updated_at'])

                Transaction.objects.filter(
                    reference=str(withdrawal.id), type='withdrawal'
                ).update(status='success')

                Notification.objects.create(
                    user=withdrawal.user,
                    title='Withdrawal Processed',
                    message=f'Your withdrawal of ${withdrawal.amount} has been processed.',
                    type='success',
                )

                send_html_email(
                subject='Withdrawal Processed',
                template_name='broadcast',
                context={'user_name': 'User', 'message': f'Your withdrawal of ${withdrawal.amount} has been successfully processed.'},
                recipient_list=[withdrawal.user.email],
            )
                return api_response(message='Withdrawal approved and marked as completed.')

            else:  # reject → refund
                withdrawal.status = 'rejected'
                withdrawal.admin_note = admin_note
                withdrawal.save()

                profile = UserProfile.objects.select_for_update().get(user=withdrawal.user)
                profile.wallet_balance += withdrawal.amount
                profile.save(update_fields=['wallet_balance', 'updated_at'])

                Transaction.objects.filter(
                    reference=str(withdrawal.id), type='withdrawal'
                ).update(status='failed')

                Notification.objects.create(
                    user=withdrawal.user,
                    title='Withdrawal Rejected',
                    message=f'Your withdrawal of ${withdrawal.amount} was rejected and refunded to your wallet. {admin_note}',
                    type='warning',
                )

                send_html_email(
                subject='Withdrawal Rejected',
                template_name='broadcast',
                context={'user_name': 'User', 'message': f'Your withdrawal of ${withdrawal.amount} was rejected. Reason: {admin_note}. The amount has been refunded to your wallet.'},
                recipient_list=[withdrawal.user.email],
            )
                return api_response(message='Withdrawal rejected and amount refunded to user wallet.')


# ─── Investment Plan Management ───────────────────────────────────────────────
@extend_schema(tags=['Admin — Plans'])
class AdminPlanListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminInvestmentPlanSerializer
    queryset = InvestmentPlan.objects.all()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return api_response(data=serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return api_response(message='Validation failed.', status_str='error', errors=serializer.errors, http_status=400)
        self.perform_create(serializer)
        return api_response(data=serializer.data, message='Investment plan created.', http_status=201)


@extend_schema(tags=['Admin — Plans'])
class AdminPlanDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminInvestmentPlanSerializer
    queryset = InvestmentPlan.objects.all()


# ─── Broadcast Email ─────────────────────────────────────────────────────────
@extend_schema(tags=['Admin — Broadcast'])
class AdminBroadcastView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(request=AdminBroadcastSerializer, summary='Broadcast email to users')
    def post(self, request):
        serializer = AdminBroadcastSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(message='Validation failed.', status_str='error', errors=serializer.errors, http_status=400)

        target = serializer.validated_data['target']
        subject = serializer.validated_data['subject']
        message = serializer.validated_data['message']

        if target == 'all':
            users = User.objects.filter(is_active=True)
        elif target == 'verified':
            users = User.objects.filter(is_active=True, is_verified=True)
        elif target == 'active_investors':
            user_ids = Investment.objects.filter(status='active').values_list('user_id', flat=True)
            users = User.objects.filter(id__in=user_ids, is_active=True)
        else:
            users = User.objects.none()

        user_list = list(users.values('id', 'email', 'first_name', 'last_name'))

        for user_data in user_list:
            full_name = f"{user_data['first_name']} {user_data['last_name']}".strip() or 'Valued Member'
            send_html_email(
                subject=subject,
                template_name='broadcast',
                context={'user_name': full_name, 'message': message},
                recipient_list=[user_data['email']],
            )

        notifications = [
            Notification(user_id=u['id'], title=subject, message=message, type='info')
            for u in user_list
        ]
        Notification.objects.bulk_create(notifications, batch_size=200)

        return api_response(message=f'Broadcast queued for {len(user_list)} users.')