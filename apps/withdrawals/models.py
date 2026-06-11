from django.db import models
from django.conf import settings
import uuid

class Withdrawal(models.Model):
   METHOD = (
      ('bitcoin', 'Bitcoin'),
      ('ethereum', 'Ethereum'),
      ('usdt', 'USDT'),
      ('bank_transfer', 'Bank Transfer')
   )

   STATUS = (
      ('pending', 'Pending'),
      ('otp_verified', 'OTP Verified'),
      ('processing', 'Processing'),
      ('completed', 'Completed'),
      ('rejected', 'Rejected')
   )

   id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
   user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='withdrawal')
   amount = models.DecimalField(max_digits=18, decimal_places=2)
   method = models.CharField(max_length=20, choices=METHOD)

   # Payout destination (snapshot from profile at time of request)
   payout_address = models.CharField(max_length=255, blank=True, null=True)
   bank_name = models.CharField(max_length=200, blank=True, null=True)
   bank_account_number = models.CharField(max_length=50, blank=True, null=True)
   bank_account_name = models.CharField(max_length=200, blank=True, null=True)

   status = models.CharField(max_length=20, choices=STATUS, default='pending')
   admin_note = models.TextField(blank=True, null=True)
   processed_at = models.DateTimeField(null=True, blank=True)
   created_at = models.DateTimeField(auto_now_add=True)
   updated_at = models.DateTimeField(auto_now=True)

   def __str__(self):
      return f'Withdrawal #{str(self.id)[:8]} - {self.user.email} - ${self.amount}'
   
   class Meta:
      db_table = 'withdrawal'
      ordering = ['-created_at']
      