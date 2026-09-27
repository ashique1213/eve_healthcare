import uuid
import secrets
from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.centres.models import CentreTest


def generate_booking_reference():
    date_str = timezone.now().strftime('%Y%m%d')
    random_hex = secrets.token_hex(3).upper()
    return f"BK-{date_str}-{random_hex}"


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        FAILED = 'FAILED', 'Failed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking_reference = models.CharField(max_length=32, unique=True, default=generate_booking_reference, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    centre_test = models.ForeignKey(CentreTest, on_delete=models.PROTECT, related_name='bookings')
    appointment_datetime = models.DateTimeField(db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['appointment_datetime']),
        ]

    def __str__(self):
        return f"{self.booking_reference} - {self.user.username} - {self.status}"

    @property
    def centre(self):
        return self.centre_test.centre

    @property
    def test(self):
        return self.centre_test.test
