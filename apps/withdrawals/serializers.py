from rest_framework import serializers
from .models import Withdrawal


PROFILE_FIELD_BY_METHOD = {
    'bitcoin': 'bitcoin_address',
    'ethereum': 'ethereum_address',
    'usdt': 'usdt_address',
    'usdt2': 'usdt_erc20_address',
}

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
                {'amount': f'Insufficient balance. Available: ${profile.wallet_balance}'}
            )

        # Check payout info is set
        payout_field = PROFILE_FIELD_BY_METHOD.get(attrs['method'])
        if not payout_field or not getattr(profile, payout_field, None):
            raise serializers.ValidationError(
                {'method': 'Please add this payout address in your profile first.'}
            )
        return attrs


class WithdrawalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Withdrawal
        fields = [
            'id', 'amount', 'method', 'payout_address',
            'status', 'admin_note', 'processed_at', 'created_at',
        ]
        read_only_fields = fields


class OTPWithdrawalVerifySerializer(serializers.Serializer):
    withdrawal_id = serializers.UUIDField()
    code = serializers.RegexField(r'^\d{6}$', max_length=6, min_length=6)
