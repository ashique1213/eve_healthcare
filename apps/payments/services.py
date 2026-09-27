import logging
import secrets
from django.db import transaction, IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import ValidationError, NotFound, PermissionDenied
from apps.bookings.models import Booking
from .models import Payment, WebhookLog

logger = logging.getLogger(__name__)


def resolve_booking(booking_identifier, user=None):
    """
    Helper function to resolve a booking by UUID or booking_reference.
    Optionally enforces user ownership check.
    """
    try:
        if len(booking_identifier) == 36 and '-' in booking_identifier:
            booking = Booking.objects.select_related('user', 'centre_test').get(id=booking_identifier)
        else:
            booking = Booking.objects.select_related('user', 'centre_test').get(booking_reference=booking_identifier)
    except (Booking.DoesNotExist, ValueError):
        raise NotFound(f"Booking with ID/reference '{booking_identifier}' was not found.")

    if user and not user.is_admin and booking.user != user:
        raise PermissionDenied("You do not have permission to access or process payment for this booking.")

    return booking


def process_simulated_payment(booking_identifier, payment_method='CARD', simulated_status='SUCCESS', idempotency_key=None, user=None):
    """
    Processes a simulated payment for a booking.
    Handles concurrency via atomic transaction and select_for_update.
    Enforces idempotency if an idempotency_key is provided.
    """
    if idempotency_key:
        existing_payment = Payment.objects.filter(idempotency_key=idempotency_key).first()
        if existing_payment:
            logger.info(f"Idempotent payment match found for key '{idempotency_key}'. Returning existing payment.")
            return existing_payment, False

    with transaction.atomic():
        booking = resolve_booking(booking_identifier, user=user)

        # Lock booking row for update
        booking = Booking.objects.select_for_update().get(id=booking.id)

        if booking.status == Booking.Status.CONFIRMED:
            raise ValidationError("This booking is already confirmed and paid for.")

        if booking.status == Booking.Status.CANCELLED:
            raise ValidationError("Cannot process payment for a cancelled booking.")

        transaction_id = f"txn_sim_{secrets.token_hex(8)}"
        
        if simulated_status == 'SUCCESS':
            booking.status = Booking.Status.CONFIRMED
            payment_status = Payment.Status.SUCCESS
        else:
            booking.status = Booking.Status.FAILED
            payment_status = Payment.Status.FAILED

        booking.save()

        payment = Payment.objects.create(
            booking=booking,
            transaction_id=transaction_id,
            idempotency_key=idempotency_key or None,
            amount=booking.amount,
            status=payment_status,
            payment_method=payment_method,
            provider_response={
                "simulated": True,
                "requested_status": simulated_status,
                "message": f"Simulated payment processed with status {simulated_status}"
            }
        )

        logger.info(f"Simulated payment {transaction_id} completed for booking {booking.booking_reference} with status {payment_status}")
        return payment, True


def process_payment_webhook(payload):
    """
    Processes an incoming payment webhook idempotently.
    Prevents duplicate payments, duplicate bookings, or corrupted state even if the same webhook is sent multiple times.
    """
    event_id = payload.get('event_id')
    event_type = payload.get('event_type')
    booking_identifier = payload.get('booking_id')
    transaction_id = payload.get('transaction_id')
    webhook_status = payload.get('status', 'SUCCESS').upper()

    if not event_id or not booking_identifier or not transaction_id:
        raise ValidationError("Missing required webhook fields: event_id, booking_id, and transaction_id are mandatory.")

    # Convert Decimal values in payload for JSON serialization compatibility
    sanitized_payload = {}
    for k, v in payload.items():
        if hasattr(v, '__float__'):
            sanitized_payload[k] = float(v)
        else:
            sanitized_payload[k] = v

    # 1. Quick pre-check for idempotency (Read path)
    if WebhookLog.objects.filter(event_id=event_id).exists():
        webhook_log = WebhookLog.objects.get(event_id=event_id)
        logger.info(f"Webhook event_id '{event_id}' already processed. Idempotency enforced.")
        return {
            "is_duplicate": True,
            "status": "already_processed",
            "message": f"Webhook event '{event_id}' has already been processed.",
            "event_id": event_id
        }

    # 2. Atomic transaction & row locks for absolute idempotency guarantee
    with transaction.atomic():
        # Atomically record/lock the webhook log to prevent race conditions from concurrent duplicate webhooks
        webhook_log, created = WebhookLog.objects.get_or_create(
            event_id=event_id,
            defaults={
                'event_type': event_type,
                'booking_reference': str(booking_identifier),
                'payload': sanitized_payload,
                'status': WebhookLog.Status.PROCESSED
            }
        )

        if not created:
            logger.info(f"Concurrent duplicate webhook event_id '{event_id}' caught by database constraint.")
            return {
                "is_duplicate": True,
                "status": "already_processed",
                "message": f"Webhook event '{event_id}' caught concurrently and ignored.",
                "event_id": event_id
            }

        # Resolve booking
        try:
            booking = resolve_booking(booking_identifier)
        except (NotFound, ValidationError) as e:
            webhook_log.status = WebhookLog.Status.FAILED
            webhook_log.error_message = str(e)
            webhook_log.save()
            raise e

        # Lock booking row for state transition
        booking = Booking.objects.select_for_update().get(id=booking.id)

        # State transition matrix
        if webhook_status == 'SUCCESS':
            if booking.status != Booking.Status.CANCELLED:
                booking.status = Booking.Status.CONFIRMED
        elif webhook_status == 'FAILED':
            if booking.status == Booking.Status.PENDING:
                booking.status = Booking.Status.FAILED

        booking.save()

        # Create or update Payment record idempotently
        payment, payment_created = Payment.objects.get_or_create(
            transaction_id=transaction_id,
            defaults={
                'booking': booking,
                'amount': payload.get('amount', booking.amount),
                'status': Payment.Status.SUCCESS if webhook_status == 'SUCCESS' else Payment.Status.FAILED,
                'payment_method': 'WEBHOOK_GATEWAY',
                'provider_response': sanitized_payload
            }
        )

        logger.info(f"Webhook {event_id} successfully processed for booking {booking.booking_reference}.")
        return {
            "is_duplicate": False,
            "status": "success",
            "message": f"Payment status for booking {booking.booking_reference} updated to {booking.status}.",
            "booking_reference": booking.booking_reference,
            "booking_status": booking.status,
            "transaction_id": transaction_id
        }
