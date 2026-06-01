from rest_framework import serializers
from apps.users.models import User, UserProfile
from apps.investments.models import InvestmentPlan, Deposit, Investment, Transaction
from apps.withdrawals.models import Withdrawal


class AdminUserSerializer(serializers.ModelSerializer):
    wallet_balance = serializers.DecimalField(
        source='profile.wallet_balance', max_digits=18, decimal_places=2, read_only=True
    )
    total_deposited = serializers.DecimalField(
        source='profile.total_deposited', max_digits=18, decimal_places=2, read_only=True
    )
    total_withdrawn = serializers.DecimalField(
        source='profile.total_withdrawn', max_digits=18, decimal_places=2, read_only=True
    )
    total_earned = serializers.DecimalField(
        source='profile.total_earned', max_digits=18, decimal_places=2, read_only=True
    )
    active_investments = serializers.SerializerMethodField()
    referral_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'phone', 'country',
            'is_active', 'is_verified', 'is_staff', 'referral_code',
            'wallet_balance', 'total_deposited', 'total_withdrawn', 'total_earned',
            'active_investments', 'referral_count', 'created_at',
        ]

    def get_active_investments(self, obj):
        return obj.investments.filter(status='active').count()

    def get_referral_count(self, obj):
        return obj.referrals.count()


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    wallet_balance = serializers.DecimalField(
        max_digits=18, decimal_places=2, required=False
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'is_active', 'is_verified', 'is_staff', 'wallet_balance']

    def update(self, instance, validated_data):
        wallet_balance = validated_data.pop('wallet_balance', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if wallet_balance is not None:
            profile = instance.profile
            profile.wallet_balance = wallet_balance
            profile.save()
        return instance


class AdminDepositSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = Deposit
        fields = [
            'id', 'user_email', 'user_name', 'amount', 'payment_method',
            'transaction_hash', 'proof_of_payment', 'status',
            'admin_note', 'confirmed_at', 'created_at',
        ]


class AdminDepositActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    admin_note = serializers.CharField(required=False, allow_blank=True)


class AdminWithdrawalSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = Withdrawal
        fields = [
            'id', 'user_email', 'user_name', 'amount', 'method',
            'payout_address', 'bank_name', 'bank_account_number', 'bank_account_name',
            'status', 'admin_note', 'processed_at', 'created_at',
        ]


class AdminWithdrawalActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    admin_note = serializers.CharField(required=False, allow_blank=True)


class AdminInvestmentPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvestmentPlan
        fields = '__all__'


class AdminPlatformStatsSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    verified_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    total_deposits = serializers.DecimalField(max_digits=18, decimal_places=2)
    total_withdrawals = serializers.DecimalField(max_digits=18, decimal_places=2)
    total_active_investments = serializers.IntegerField()
    total_completed_investments = serializers.IntegerField()
    pending_deposits = serializers.IntegerField()
    pending_withdrawals = serializers.IntegerField()
    total_platform_balance = serializers.DecimalField(max_digits=18, decimal_places=2)


class AdminBroadcastSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=200)
    message = serializers.CharField()
    target = serializers.ChoiceField(choices=['all', 'verified', 'active_investors'])


class AdminCreditWalletSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    description = serializers.CharField(max_length=255, default='Manual credit by admin')
