from rest_framework import permissions, status, views
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse
from .models import Payment, WebhookLog
from .serializers import (
    PaymentSerializer,
    SimulatedPaymentRequestSerializer,
    PaymentWebhookSerializer
)
from .services import process_simulated_payment, process_payment_webhook
from .tasks import send_booking_confirmation_notification


@extend_schema_view(
    post=extend_schema(
        summary="Simulate a diagnostic booking payment",
        tags=["Payments"],
        request=SimulatedPaymentRequestSerializer,
        responses={
            200: PaymentSerializer,
            400: OpenApiResponse(description="Invalid booking status or request payload"),
            404: OpenApiResponse(description="Booking not found"),
        }
    )
)
class SimulatedPaymentView(views.APIView):
    """
    Endpoint for simulating payment processing for a diagnostic booking.
    Accepts booking_id and simulated status (SUCCESS or FAILED).
    Updates booking status accordingly.
    """
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'payment'

    def post(self, request, *args, **kwargs):
        serializer = SimulatedPaymentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        booking_id = serializer.validated_data['booking_id']
        payment_method = serializer.validated_data.get('payment_method', 'CARD')
        simulated_status = serializer.validated_data.get('status', 'SUCCESS')
        idempotency_key = serializer.validated_data.get('idempotency_key') or request.headers.get('X-Idempotency-Key')

        payment, created = process_simulated_payment(
            booking_identifier=booking_id,
            payment_method=payment_method,
            simulated_status=simulated_status,
            idempotency_key=idempotency_key,
            user=request.user
        )

        # Trigger async notification background task if payment confirmed
        if payment.status == Payment.Status.SUCCESS:
            try:
                send_booking_confirmation_notification.delay(str(payment.booking.id))
            except Exception:
                pass  # Fallback if Celery worker is offline

        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(PaymentSerializer(payment).data, status=response_status)


@extend_schema_view(
    post=extend_schema(
        summary="Payment Provider Webhook Endpoint (Idempotent)",
        tags=["Payments"],
        request=PaymentWebhookSerializer,
        responses={
            200: OpenApiResponse(description="Webhook processed or duplicate event safely ignored"),
            400: OpenApiResponse(description="Invalid webhook payload"),
        }
    )
)
class PaymentWebhookView(views.APIView):
    """
    Webhook endpoint to receive payment status updates from a simulated payment gateway.
    GUARANTEED IDEMPOTENT: Duplicate event IDs or retry deliveries will NOT create duplicate payments or corrupt booking state.
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'webhook'

    def post(self, request, *args, **kwargs):
        serializer = PaymentWebhookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = process_payment_webhook(serializer.validated_data)

        # Always return HTTP 200 OK for valid webhooks (including duplicates) so payment gateway doesn't un-necessarily retry
        return Response(result, status=status.HTTP_200_OK)


@extend_schema_view(
    get=extend_schema(summary="List user payment transaction history", tags=["Payments"], responses={200: PaymentSerializer(many=True)})
)
class PaymentHistoryListView(views.APIView):
    """
    List payment transaction history for current user or all transactions for Admin.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.is_admin:
            payments = Payment.objects.select_related('booking').all()
        else:
            payments = Payment.objects.select_related('booking').filter(booking__user=user)
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
