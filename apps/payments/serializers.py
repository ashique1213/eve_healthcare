from rest_framework import serializers
from .models import Payment, WebhookLog


class PaymentSerializer(serializers.ModelSerializer):
    booking_reference = serializers.CharField(source='booking.booking_reference', read_only=True)

    class Meta:
        model = Payment
        fields = (
            'id',
            'transaction_id',
            'idempotency_key',
            'booking',
            'booking_reference',
            'amount',
            'status',
            'payment_method',
            'provider_response',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


class SimulatedPaymentRequestSerializer(serializers.Serializer):
    booking_id = serializers.CharField(
        required=True,
        help_text="UUID or Booking Reference (e.g., BK-20260925-A1B2C3)"
    )
    payment_method = serializers.CharField(default='CARD', required=False)
    status = serializers.ChoiceField(
        choices=['SUCCESS', 'FAILED'],
        default='SUCCESS',
        help_text="Simulated outcome for testing: SUCCESS or FAILED"
    )
    idempotency_key = serializers.CharField(required=False, allow_blank=True, max_length=128)


class PaymentWebhookSerializer(serializers.Serializer):
    event_id = serializers.CharField(required=True, max_length=128, help_text="Unique event identifier for idempotency")
    event_type = serializers.CharField(required=True, max_length=64, help_text="e.g. payment.success, payment.failed")
    booking_id = serializers.CharField(required=True, help_text="Booking UUID or Booking Reference")
    transaction_id = serializers.CharField(required=True, max_length=64)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    status = serializers.ChoiceField(choices=['SUCCESS', 'FAILED'], required=True)
