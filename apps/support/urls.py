from django.urls import path

from .views import (
    AdminSupportTicketActionView,
    AdminSupportTicketListView,
    SupportTicketDetailView,
    SupportTicketListCreateView,
    SupportTicketReplyView,
)

urlpatterns = [
    path('tickets/', SupportTicketListCreateView.as_view(), name='support-ticket-list-create'),
    path('tickets/<uuid:pk>/', SupportTicketDetailView.as_view(), name='support-ticket-detail'),
    path('tickets/<uuid:pk>/reply/', SupportTicketReplyView.as_view(), name='support-ticket-reply'),
    path('admin/tickets/', AdminSupportTicketListView.as_view(), name='admin-support-ticket-list'),
    path('admin/tickets/<uuid:pk>/action/', AdminSupportTicketActionView.as_view(), name='admin-support-ticket-action'),
]
