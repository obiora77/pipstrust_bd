from rest_framework import serializers
from .models import Withdrawal


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Withdrawal
        fields = ['amount', 'method']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than zero.')
        return value

    def validate(self, attrs):
        user = self.context['request'].user
        profile = user.profile

        if attrs['amount'] > profile.wallet_balance:
            raise serializers.ValidationError(
                f'Insufficient balance. Available: ${profile.wallet_balance}'
            )

        # Check payout info is set
        method = attrs['method']
        if method == 'bitcoin' and not profile.bitcoin_address:
            raise serializers.ValidationError('Please add your Bitcoin address in your profile first.')
        elif method == 'ethereum' and not profile.ethereum_address:
            raise serializers.ValidationError('Please add your Ethereum address in your profile first.')
        elif method == 'usdt' and not profile.usdt_address:
            raise serializers.ValidationError('Please add your USDT address in your profile first.')

        return attrs


class WithdrawalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Withdrawal
        fields = [
            'id', 'amount', 'method', 'payout_address',
            'status', 'admin_note', 'processed_at', 'created_at',
        ]
        read_only_fields = ['status', 'admin_note', 'processed_at', 'payout_address']


class OTPWithdrawalVerifySerializer(serializers.Serializer):
    withdrawal_id = serializers.UUIDField()
    code = serializers.CharField(max_length=6)
