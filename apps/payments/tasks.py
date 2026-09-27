import logging
from celery import shared_task
from apps.bookings.models import Booking

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def send_booking_confirmation_notification(self, booking_id):
    """
    Background job to send simulated booking confirmation notifications (Email/SMS).
    Includes automatic retries in case of transient failures.
    """
    try:
        booking = Booking.objects.select_related('user', 'centre_test__centre', 'centre_test__test').get(id=booking_id)
        logger.info(
            f"[BACKGROUND JOB] Sending booking confirmation to {booking.user.email} for booking {booking.booking_reference}. "
            f"Test: {booking.test.name} at {booking.centre.name}."
        )
        return f"Notification sent for {booking.booking_reference}"
    except Exception as exc:
        logger.error(f"[BACKGROUND JOB FAILED] Retrying notification for booking {booking_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task
def cleanup_expired_pending_bookings():
    """
    Periodic background job to clean up or mark stale PENDING bookings (e.g. pending > 24h) as FAILED/EXPIRED.
    """
    from django.utils import timezone
    from datetime import timedelta

    cutoff_time = timezone.now() - timedelta(hours=24)
    stale_bookings = Booking.objects.filter(status=Booking.Status.PENDING, created_at__lt=cutoff_time)
    count = stale_bookings.update(status=Booking.Status.FAILED)
    logger.info(f"[BACKGROUND JOB] Cleaned up {count} expired pending bookings.")
    return count
