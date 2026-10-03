from django.contrib import admin

from .models import SupportTicket, TicketMessage


class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 0
    readonly_fields = ('sender', 'message', 'created_at')


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'subject', 'category', 'priority', 'status', 'updated_at')
    list_filter = ('status', 'category', 'priority')
    search_fields = ('user__email', 'subject')
    inlines = [TicketMessageInline]
