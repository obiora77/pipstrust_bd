from django.test import TestCase
from rest_framework.test import APIClient

from apps.users.models import User, UserProfile

from .models import SupportTicket


class SupportTicketTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='support@example.com', password='StrongPass123!',
            first_name='Support', last_name='User', is_verified=True,
        )
        UserProfile.objects.create(user=self.user)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_user_can_create_and_reply_to_own_ticket(self):
        response = self.client.post('/api/support/tickets/', {
            'subject': 'Withdrawal help',
            'category': 'withdrawal',
            'priority': 'normal',
            'message': 'Please check my request.',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        ticket = SupportTicket.objects.get(id=response.data['data']['id'])
        self.assertEqual(ticket.messages.count(), 1)

        reply = self.client.post(f'/api/support/tickets/{ticket.id}/reply/', {
            'message': 'Adding another detail.',
        }, format='json')
        self.assertEqual(reply.status_code, 200)
        self.assertEqual(ticket.messages.count(), 2)
