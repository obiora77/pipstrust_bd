from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db import transaction
from drf_spectacular.utils import extend_schema

from apps.admin_api.permissions import IsAdminUser
from apps.notifications.models import Notification
from apps.users.views import api_response

from .models import SupportTicket, TicketMessage
from .serializers import (
    AdminTicketUpdateSerializer,
    SupportTicketCreateSerializer,
    SupportTicketSerializer,
    TicketReplySerializer,
)


@extend_schema(tags=['Support'])
class SupportTicketListCreateView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tickets = SupportTicket.objects.filter(user=request.user).prefetch_related('messages')
        return api_response(data=SupportTicketSerializer(tickets, many=True).data)

    @extend_schema(request=SupportTicketCreateSerializer)
    def post(self, request):
        serializer = SupportTicketCreateSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return api_response(
                message='Validation failed.', status_str='error',
                errors=serializer.errors, http_status=400,
            )
        ticket = serializer.save()
        return api_response(
            data=SupportTicketSerializer(ticket).data,
            message='Support ticket created successfully.', http_status=201,
        )


@extend_schema(tags=['Support'])
class SupportTicketDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        ticket = SupportTicket.objects.filter(user=request.user, id=pk).prefetch_related('messages').first()
        if not ticket:
            return api_response(message='Ticket not found.', status_str='error', http_status=404)
        return api_response(data=SupportTicketSerializer(ticket).data)


@extend_schema(tags=['Support'])
class SupportTicketReplyView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=TicketReplySerializer)
    def post(self, request, pk):
        serializer = TicketReplySerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(message='Validation failed.', status_str='error', errors=serializer.errors, http_status=400)

        with transaction.atomic():
            ticket = SupportTicket.objects.select_for_update().filter(user=request.user, id=pk).first()
            if not ticket:
                return api_response(message='Ticket not found.', status_str='error', http_status=404)
            if ticket.status == 'closed':
                return api_response(message='This ticket is closed.', status_str='error', http_status=400)
            TicketMessage.objects.create(ticket=ticket, sender='user', message=serializer.validated_data['message'].strip())
            ticket.status = 'open'
            ticket.save(update_fields=['status', 'updated_at'])

        return api_response(data=SupportTicketSerializer(ticket).data, message='Reply sent.')


@extend_schema(tags=['Admin — Support'])
class AdminSupportTicketListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        tickets = SupportTicket.objects.select_related('user').prefetch_related('messages').all()
        status_value = request.query_params.get('status')
        if status_value:
            tickets = tickets.filter(status=status_value)
        data = SupportTicketSerializer(tickets, many=True).data
        for row, ticket in zip(data, tickets):
            row['user_email'] = ticket.user.email
            row['user_name'] = ticket.user.full_name
        return api_response(data=data)


@extend_schema(tags=['Admin — Support'])
class AdminSupportTicketActionView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(request=AdminTicketUpdateSerializer)
    def post(self, request, pk):
        serializer = AdminTicketUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(message='Validation failed.', status_str='error', errors=serializer.errors, http_status=400)

        with transaction.atomic():
            ticket = SupportTicket.objects.select_for_update().select_related('user').filter(id=pk).first()
            if not ticket:
                return api_response(message='Ticket not found.', status_str='error', http_status=404)

            message = serializer.validated_data.get('message')
            if message:
                TicketMessage.objects.create(ticket=ticket, sender='admin', message=message.strip())
                ticket.status = 'answered'
                Notification.objects.create(
                    user=ticket.user,
                    title='Support replied',
                    message=f'You have a new reply on “{ticket.subject}”.',
                    type='info',
                )
            if 'status' in serializer.validated_data:
                ticket.status = serializer.validated_data['status']
            ticket.save(update_fields=['status', 'updated_at'])

        return api_response(data=SupportTicketSerializer(ticket).data, message='Ticket updated.')
