import uuid
from django.db import models
from django.conf import settings


class InvestmentPlan(models.Model):
   DURATION_UNIT = (
      ('days', 'Days'),
      ('weeks', 'Weeks'),
      ('months', 'Months')
   )

   id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
   name = models.CharField(max_length=100)
   description = models.TextField(blank=True)
   min_amount = models.DecimalField(max_digits=18, decimal_places=2)
   max_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
   roi_percentage = models.DecimalField(max_digits=5, decimal_places=2)
   duration = models.PositiveIntegerField()
   duration_unit = models.CharField(max_length=10, choices=DURATION_UNIT, default='days')
   is_active = models.BooleanField(default=True)
   is_featured = models.BooleanField(default=False)
   create_at = models.DateTimeField(auto_now_add=True)

   def __str__(self):
      return f'{self.name} - {self.roi_percentage}% / {self.duration} {self.duration_unit}'
   
   class Meta:
      db_table = 'investment_plans'
      ordering = ['min_amount']


class Deposit(models.Model):
   PAYMENT_METHOD = (
      ('bitcoin', 'Bitcoin'),
      ('ethereum', 'Ethereum'),
      ('usdt', 'USDT'),
      ('bank_transfer', 'Bank Transfer'),
   )

   STATUS = (
      ('pending', 'Pending'),
      ('confirmed', 'Confirmed'),
      ('rejected', 'Rejected'),
   )

   id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
   user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='deposits')
   amount = models.DecimalField(max_digits=18, decimal_places=2)
   payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD)
   transaction_hash = models.CharField(max_length=255, blank=True, null=True)
   proof_of_payment = models.ImageField(upload_to='deposit_proofs/', blank=True, null=True)
   status = models.CharField(max_length=20, choices=STATUS, default='pending')
   admin_note = models.TextField(blank=True, null=True)
   confirmed_at = models.DateTimeField(null=True, blank=True)
   created_at = models.DateTimeField(auto_now_add=True)
   updated_at = models.DateTimeField(auto_now=True)

   def __str__(self):
      return f'Deposit #{str(self.id)[:8]} — {self.user.email} — ${self.amount}'

   class Meta:
      db_table = 'deposits'
      ordering = ['-created_at']


class Investment(models.Model):
    STATUS = (
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='investments')
    plan = models.ForeignKey(InvestmentPlan, on_delete=models.PROTECT, related_name='investments')
    deposit = models.OneToOneField(Deposit, on_delete=models.PROTECT, related_name='investment', null=True, blank=True)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    roi_percentage = models.DecimalField(max_digits=5, decimal_places=2)  # snapshot at time of investment
    expected_return = models.DecimalField(max_digits=18, decimal_places=2)
    actual_return = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS, default='active')
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Investment #{str(self.id)[:8]} — {self.user.email} — ${self.amount}'

    @property
    def progress_percentage(self):
        from django.utils import timezone
        now = timezone.now()
        if now >= self.ends_at:
            return 100
        total = (self.ends_at - self.starts_at).total_seconds()
        elapsed = (now - self.starts_at).total_seconds()
        return min(round((elapsed / total) * 100, 2), 100)

    class Meta:
        db_table = 'investments'
        ordering = ['-created_at']


class Transaction(models.Model):
    TYPE = (
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('roi', 'ROI Credit'),
        ('referral_bonus', 'Referral Bonus'),
    )

    STATUS = (
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    type = models.CharField(max_length=20, choices=TYPE)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    description = models.CharField(max_length=255, blank=True)
    reference = models.CharField(max_length=100, blank=True)  # external ref or internal id
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.type} — {self.user.email} — ${self.amount}'

    class Meta:
        db_table = 'transactions'
        ordering = ['-created_at']
