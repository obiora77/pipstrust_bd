import uuid

from django.conf import settings
from django.db import models


class SupportTicket(models.Model):
    CATEGORY_CHOICES = (
        ('account', 'Account'),
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('investment', 'Investment'),
        ('technical', 'Technical'),
        ('other', 'Other'),
    )
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
    )
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('answered', 'Answered'),
        ('closed', 'Closed'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_tickets')
    subject = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'support_tickets'
        ordering = ['-updated_at']

    def __str__(self):
        return f'#{str(self.id)[:8]} {self.subject}'


class TicketMessage(models.Model):
    SENDER_CHOICES = (('user', 'User'), ('admin', 'Admin'))

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'support_ticket_messages'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.ticket_id} - {self.sender}'
