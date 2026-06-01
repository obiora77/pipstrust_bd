from django.urls import path
from .views import (
    WithdrawalRequestView, WithdrawalOTPVerifyView,
    WithdrawalListView, WithdrawalDetailView, WithdrawalCancelView,
)

urlpatterns = [
    path('', WithdrawalListView.as_view(), name='withdrawal-list'),
    path('request/', WithdrawalRequestView.as_view(), name='withdrawal-request'),
    path('verify-otp/', WithdrawalOTPVerifyView.as_view(), name='withdrawal-verify-otp'),
    path('<uuid:pk>/', WithdrawalDetailView.as_view(), name='withdrawal-detail'),
    path('<uuid:pk>/cancel/', WithdrawalCancelView.as_view(), name='withdrawal-cancel'),
]
