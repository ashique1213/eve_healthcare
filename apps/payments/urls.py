from django.urls import path
from .views import SimulatedPaymentView, PaymentWebhookView, PaymentHistoryListView

urlpatterns = [
    path('', SimulatedPaymentView.as_view(), name='payment-process'),
    path('webhook/', PaymentWebhookView.as_view(), name='payment-webhook'),
    path('history/', PaymentHistoryListView.as_view(), name='payment-history'),
]
