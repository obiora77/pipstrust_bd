from rest_framework import serializers
from .models import InvestmentPlan, Deposit, Investment, Transaction


class InvestmentPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvestmentPlan
        fields = [
            'id', 'name', 'description', 'min_amount', 'max_amount',
            'roi_percentage', 'duration', 'duration_unit',
            'is_active', 'is_featured', 'created_at',
        ]


class DepositCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deposit
        fields = ['amount', 'payment_method', 'transaction_hash', 'proof_of_payment']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than zero.')
        return value


class DepositSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Deposit
        fields = [
            'id', 'user_email', 'amount', 'payment_method',
            'transaction_hash', 'proof_of_payment', 'status',
            'admin_note', 'confirmed_at', 'created_at',
        ]
        read_only_fields = ['status', 'admin_note', 'confirmed_at']


class InvestmentCreateSerializer(serializers.Serializer):
    plan_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)

    def validate(self, attrs):
        user = self.context['request'].user

        plan = InvestmentPlan.objects.filter(id=attrs['plan_id'], is_active=True).first()
        if not plan:
            raise serializers.ValidationError({'plan_id': 'Investment plan not found or inactive.'})

        amount = attrs['amount']
        if amount <= 0:
            raise serializers.ValidationError({'amount': 'Amount must be greater than zero.'})

        if amount < plan.min_amount:
            raise serializers.ValidationError(
                {'amount': f'Minimum investment for this plan is ${plan.min_amount}.'}
            )

        if plan.max_amount and amount > plan.max_amount:
            raise serializers.ValidationError(
                {'amount': f'Maximum investment for this plan is ${plan.max_amount}.'}
            )

        profile = user.profile
        if profile.wallet_balance < amount:
            raise serializers.ValidationError(
                {'amount': f'Insufficient wallet balance. Available: ${profile.wallet_balance}.'}
            )

        attrs['plan'] = plan
        return attrs


class InvestmentSerializer(serializers.ModelSerializer):
    plan = InvestmentPlanSerializer(read_only=True)
    progress_percentage = serializers.ReadOnlyField()

    class Meta:
        model = Investment
        fields = [
            'id', 'plan', 'amount', 'roi_percentage',
            'expected_return', 'actual_return', 'status',
            'starts_at', 'ends_at', 'completed_at',
            'progress_percentage', 'created_at',
        ]


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'type', 'amount', 'status', 'description', 'reference', 'created_at']


class DashboardSummarySerializer(serializers.Serializer):
    wallet_balance = serializers.DecimalField(max_digits=18, decimal_places=2)
    total_deposited = serializers.DecimalField(max_digits=18, decimal_places=2)
    total_withdrawn = serializers.DecimalField(max_digits=18, decimal_places=2)
    total_earned = serializers.DecimalField(max_digits=18, decimal_places=2)
    active_investments = serializers.IntegerField()
    completed_investments = serializers.IntegerField()
    pending_deposits = serializers.IntegerField()
    referral_count = serializers.IntegerField()