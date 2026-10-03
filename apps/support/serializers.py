from rest_framework import serializers

from .models import SupportTicket, TicketMessage


class TicketMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketMessage
        fields = ['id', 'sender', 'message', 'created_at']
        read_only_fields = fields


class SupportTicketSerializer(serializers.ModelSerializer):
    messages = TicketMessageSerializer(many=True, read_only=True)

    class Meta:
        model = SupportTicket
        fields = [
            'id', 'subject', 'category', 'priority', 'status',
            'messages', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'status', 'messages', 'created_at', 'updated_at']


class SupportTicketCreateSerializer(serializers.ModelSerializer):
    message = serializers.CharField(write_only=True, min_length=2)

    class Meta:
        model = SupportTicket
        fields = ['subject', 'category', 'priority', 'message']

    def create(self, validated_data):
        message = validated_data.pop('message')
        ticket = SupportTicket.objects.create(user=self.context['request'].user, **validated_data)
        TicketMessage.objects.create(ticket=ticket, sender='user', message=message.strip())
        return ticket


class TicketReplySerializer(serializers.Serializer):
    message = serializers.CharField(min_length=2)


class AdminTicketUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['open', 'answered', 'closed'], required=False)
    message = serializers.CharField(min_length=2, required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError('Provide a status or message.')
        return attrs
