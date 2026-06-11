from django.contrib import admin
from django.utils import timezone
from django.db import transaction as db_transaction
from .models import Withdrawal
from apps.investments.models import Transaction
from apps.notifications.models import Notification
from apps.notifications.email_utils import send_html_email


@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'amount', 'method', 'status', 'created_at']
    list_filter = ['status', 'method']
    search_fields = ['user__email']
    actions = ['mark_completed', 'mark_processing', 'reject_withdrawals']

    def mark_completed(self, request, queryset):
        with db_transaction.atomic():
            for w in queryset.filter(status__in=['otp_verified', 'processing']):
                w.status = 'completed'
                w.processed_at = timezone.now()
                w.save()

                profile = w.user.profile
                profile.total_withdrawn += w.amount
                profile.save()

                Transaction.objects.filter(
                    reference=str(w.id), type='withdrawal'
                ).update(status='success')

                Notification.objects.create(
                    user=w.user,
                    title='Withdrawal Processed',
                    message=f'Your withdrawal of ${w.amount} has been processed.',
                    type='success',
                )

                send_html_email(
                    subject='Withdrawal Processed - PipsTrust',
                    template_name='withdrawal_processed',
                    context={
                        'user': w.user,
                        'user_name': w.user.full_name,
                        'amount': w.amount,
                        'method': w.get_method_display(),
                        'payout_address': w.payout_address or w.bank_account_number or 'N/A',
                        'date': timezone.now().strftime('%B %d, %Y %I:%M %p UTC'),
                    },
                    recipient_list=[w.user.email],
                )

        self.message_user(request, 'Selected withdrawals marked as completed.')
    mark_completed.short_description = 'Mark as Completed'

    def mark_processing(self, request, queryset):
        queryset.filter(status='otp_verified').update(status='processing')
        self.message_user(request, 'Selected withdrawals marked as processing.')
    mark_processing.short_description = 'Mark as Processing'

    def reject_withdrawals(self, request, queryset):
        with db_transaction.atomic():
            for w in queryset.filter(status__in=['pending', 'otp_verified']):
                w.status = 'rejected'
                w.save()

                profile = w.user.profile
                profile.wallet_balance += w.amount
                profile.save()

                Transaction.objects.filter(
                    reference=str(w.id), type='withdrawal'
                ).update(status='failed')

                Notification.objects.create(
                    user=w.user,
                    title='Withdrawal Rejected',
                    message=f'Your withdrawal of ${w.amount} was rejected and refunded to your wallet.',
                    type='warning',
                )

                send_html_email(
                    subject='Withdrawal Rejected - PipsTrust',
                    template_name='withdrawal_rejected',
                    context={
                        'user': w.user,
                        'user_name': w.user.full_name,
                        'amount': w.amount,
                        'method': w.get_method_display(),
                        'date': timezone.now().strftime('%B %d, %Y %I:%M %p UTC'),
                    },
                    recipient_list=[w.user.email],
                )

        self.message_user(request, 'Selected withdrawals rejected and refunded.')
    reject_withdrawals.short_description = 'Reject & Refund'