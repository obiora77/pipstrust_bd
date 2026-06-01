from django.urls import path
from .views import (
    AdminPlatformStatsView,
    AdminUserListView, AdminUserDetailView,
    AdminToggleUserStatusView, AdminCreditWalletView,
    AdminDepositListView, AdminDepositDetailView, AdminDepositActionView,
    AdminWithdrawalListView, AdminWithdrawalDetailView, AdminWithdrawalActionView,
    AdminPlanListCreateView, AdminPlanDetailView,
    AdminBroadcastView,
)

urlpatterns = [
    # Stats
    path('stats/', AdminPlatformStatsView.as_view(), name='admin-stats'),

    # Users
    path('users/', AdminUserListView.as_view(), name='admin-user-list'),
    path('users/<uuid:pk>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('users/<uuid:pk>/toggle-status/', AdminToggleUserStatusView.as_view(), name='admin-toggle-user'),
    path('users/credit-wallet/', AdminCreditWalletView.as_view(), name='admin-credit-wallet'),

    # Deposits
    path('deposits/', AdminDepositListView.as_view(), name='admin-deposit-list'),
    path('deposits/<uuid:pk>/', AdminDepositDetailView.as_view(), name='admin-deposit-detail'),
    path('deposits/<uuid:pk>/action/', AdminDepositActionView.as_view(), name='admin-deposit-action'),

    # Withdrawals
    path('withdrawals/', AdminWithdrawalListView.as_view(), name='admin-withdrawal-list'),
    path('withdrawals/<uuid:pk>/', AdminWithdrawalDetailView.as_view(), name='admin-withdrawal-detail'),
    path('withdrawals/<uuid:pk>/action/', AdminWithdrawalActionView.as_view(), name='admin-withdrawal-action'),

    # Investment Plans
    path('plans/', AdminPlanListCreateView.as_view(), name='admin-plan-list'),
    path('plans/<uuid:pk>/', AdminPlanDetailView.as_view(), name='admin-plan-detail'),

    # Broadcast
    path('broadcast/', AdminBroadcastView.as_view(), name='admin-broadcast'),
]
