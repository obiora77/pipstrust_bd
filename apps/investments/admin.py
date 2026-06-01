from django.contrib import admin
from django.utils import timezone
from django.db import transaction as db_transaction
from .models import InvestmentPlan, Deposit, Investment, Transaction
from apps.notifications.tasks import send_notification_email


@admin.register(InvestmentPlan)
class InvestmentPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'roi_percentage', 'duration', 'duration_unit', 'min_amount', 'max_amount', 'is_active', 'is_featured']
    list_filter = ['is_active', 'is_featured', 'duration_unit']
    search_fields = ['name']


@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'amount', 'payment_method', 'status', 'created_at']
    list_filter = ['status', 'payment_method']
    search_fields = ['user__email', 'transaction_hash']
    actions = ['approve_deposits', 'reject_deposits']

    def approve_deposits(self, request, queryset):
        with db_transaction.atomic():
            for deposit in queryset.filter(status='pending'):
                deposit.status = 'confirmed'
                deposit.confirmed_at = timezone.now()
                deposit.save()

                # Update wallet balance
                profile = deposit.user.profile
                profile.wallet_balance += deposit.amount
                profile.save()

                # Log transaction
                from apps.investments.models import Transaction
                Transaction.objects.filter(
                    reference=str(deposit.id), type='deposit'
                ).update(status='success')

                # Notify user
                send_notification_email.delay(
                    subject='Deposit Confirmed',
                    message=f'Your deposit of ${deposit.amount} has been confirmed and added to your wallet.',
                    recipient_list=[deposit.user.email],
                )
        self.message_user(request, 'Selected deposits approved successfully.')
    approve_deposits.short_description = 'Approve selected deposits'

    def reject_deposits(self, request, queryset):
        queryset.filter(status='pending').update(status='rejected')
        self.message_user(request, 'Selected deposits rejected.')
    reject_deposits.short_description = 'Reject selected deposits'


@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'plan', 'amount', 'expected_return', 'status', 'ends_at']
    list_filter = ['status', 'plan']
    search_fields = ['user__email']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'type', 'amount', 'status', 'created_at']
    list_filter = ['type', 'status']
    search_fields = ['user__email', 'reference']
