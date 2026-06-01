from django.urls import path
from .views import (
    InvestmentPlanListView,
    DepositCreateView, DepositListView, DepositDetailView,
    InvestmentCreateView, InvestmentListView, InvestmentDetailView,
    TransactionListView, DashboardSummaryView,
)

urlpatterns = [
    # Plans
    path('plans/', InvestmentPlanListView.as_view(), name='plan-list'),

    # Deposits
    path('deposits/', DepositListView.as_view(), name='deposit-list'),
    path('deposits/create/', DepositCreateView.as_view(), name='deposit-create'),
    path('deposits/<uuid:pk>/', DepositDetailView.as_view(), name='deposit-detail'),

    # Investments
    path('', InvestmentListView.as_view(), name='investment-list'),
    path('create/', InvestmentCreateView.as_view(), name='investment-create'),
    path('<uuid:pk>/', InvestmentDetailView.as_view(), name='investment-detail'),

    # Transactions
    path('transactions/', TransactionListView.as_view(), name='transaction-list'),

    # Dashboard
    path('dashboard/', DashboardSummaryView.as_view(), name='dashboard-summary'),
]
