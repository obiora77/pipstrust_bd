from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.utils import timezone
from django.db import transaction as db_transaction
from drf_spectacular.utils import extend_schema
from datetime import timedelta

from .models import InvestmentPlan, Deposit, Investment, Transaction
from .serializers import (
    InvestmentPlanSerializer, DepositCreateSerializer, DepositSerializer,
    InvestmentCreateSerializer, InvestmentSerializer,
    TransactionSerializer, DashboardSummarySerializer,
)
from apps.notifications.tasks import send_notification_email

# ─── Investment Plans ─────────────────────────────────────────────────────────
@extend_schema(tags=['Plans'])
class InvestmentPlanListView(generics.ListAPIView):
    """List all active investment plans. Public endpoint."""
    serializer_class = InvestmentPlanSerializer
    permission_classes = [AllowAny]
    queryset = InvestmentPlan.objects.filter(is_active=True)

# ─── Deposits ─────────────────────────────────────────────────────────────────
@extend_schema(tags=['Deposits'])
class DepositCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(request=DepositCreateSerializer, summary='Submit a deposit')
    def post(self, request):
        serializer = DepositCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        deposit = serializer.save(user=request.user)

        # Log transaction
        Transaction.objects.create(
            user=request.user,
            type='deposit',
            amount=deposit.amount,
            status='pending',
            description=f'Deposit via {deposit.get_payment_method_display()}',
            reference=str(deposit.id),
        )

        # Notify admins
        send_notification_email.delay(
            subject='New Deposit Submitted',
            message=f'User {request.user.email} submitted a deposit of ${deposit.amount} via {deposit.payment_method}.',
            recipient_list=None,  # sends to admin
        )

        return Response(DepositSerializer(deposit).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Deposits'])
class DepositListView(generics.ListAPIView):
    """List current user's deposits."""
    serializer_class = DepositSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'payment_method']
    ordering_fields = ['created_at', 'amount']

    def get_queryset(self):
        return Deposit.objects.filter(user=self.request.user)


@extend_schema(tags=['Deposits'])
class DepositDetailView(generics.RetrieveAPIView):
    serializer_class = DepositSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Deposit.objects.filter(user=self.request.user)

# ─── Investments ──────────────────────────────────────────────────────────────
@extend_schema(tags=['Investments'])
class InvestmentCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=InvestmentCreateSerializer, summary='Start an investment from a confirmed deposit')
    def post(self, request):
        serializer = InvestmentCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        plan = serializer.validated_data['plan']
        deposit = serializer.validated_data['deposit']

        # Compute duration in days
        duration_days = plan.duration
        if plan.duration_unit == 'weeks':
            duration_days = plan.duration * 7
        elif plan.duration_unit == 'months':
            duration_days = plan.duration * 30

        now = timezone.now()
        expected_return = deposit.amount * (plan.roi_percentage / 100) + deposit.amount

        with db_transaction.atomic():
            investment = Investment.objects.create(
                user=request.user,
                plan=plan,
                deposit=deposit,
                amount=deposit.amount,
                roi_percentage=plan.roi_percentage,
                expected_return=expected_return,
                starts_at=now,
                ends_at=now + timedelta(days=duration_days),
            )

            # Update user profile
            profile = request.user.profile
            profile.total_deposited += deposit.amount
            profile.save()

        send_notification_email.delay(
            subject='Investment Started',
            message=f'Your investment of ${deposit.amount} on the {plan.name} plan has started. Expected return: ${expected_return}.',
            recipient_list=[request.user.email],
        )

        return Response(InvestmentSerializer(investment).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Investments'])
class InvestmentListView(generics.ListAPIView):
    serializer_class = InvestmentSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status']
    ordering_fields = ['created_at', 'amount', 'ends_at']

    def get_queryset(self):
        return Investment.objects.filter(user=self.request.user).select_related('plan')


@extend_schema(tags=['Investments'])
class InvestmentDetailView(generics.RetrieveAPIView):
    serializer_class = InvestmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Investment.objects.filter(user=self.request.user).select_related('plan')

# ─── Transactions ─────────────────────────────────────────────────────────────
@extend_schema(tags=['Transactions'])
class TransactionListView(generics.ListAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['type', 'status']
    search_fields = ['description', 'reference']
    ordering_fields = ['created_at', 'amount']

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

# ─── Dashboard Summary ────────────────────────────────────────────────────────
@extend_schema(tags=['Dashboard'])
class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=DashboardSummarySerializer, summary='Get user dashboard summary')
    def get(self, request):
        user = request.user
        profile = user.profile
        data = {
            'wallet_balance': profile.wallet_balance,
            'total_deposited': profile.total_deposited,
            'total_withdrawn': profile.total_withdrawn,
            'total_earned': profile.total_earned,
            'active_investments': user.investments.filter(status='active').count(),
            'completed_investments': user.investments.filter(status='completed').count(),
            'pending_deposits': user.deposits.filter(status='pending').count(),
            'referral_count': user.referrals.count(),
        }
        return Response(DashboardSummarySerializer(data).data)