import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from apps.centres.models import DiagnosticCentre, DiagnosticTest, CentreTest
from apps.bookings.models import Booking
from apps.payments.models import Payment, WebhookLog

User = get_user_model()


@pytest.mark.django_db
class TestIdempotentWebhook:
    def setup_method(self):
        self.client = APIClient()
        self.patient = User.objects.create_user(
            username="webhook_user",
            email="webhook@test.com",
            password="Password123!",
            role=User.Role.PATIENT
        )
        self.centre = DiagnosticCentre.objects.create(name="HealthCare Lab", location="Whitefield", city="Bangalore", address="Main Rd")
        self.test = DiagnosticTest.objects.create(name="HbA1c Diabetes", code="HBA1C-01")
        self.centre_test = CentreTest.objects.create(centre=self.centre, test=self.test, price=600.00)

        self.booking = Booking.objects.create(
            user=self.patient,
            centre_test=self.centre_test,
            amount=600.00,
            appointment_datetime=timezone.now() + timedelta(days=2),
            status=Booking.Status.PENDING
        )
        self.webhook_url = reverse('payment-webhook')

    def test_webhook_first_delivery_confirms_booking(self):
        payload = {
            "event_id": "evt_unique_1001",
            "event_type": "payment.success",
            "booking_id": str(self.booking.id),
            "transaction_id": "txn_gateway_9999",
            "amount": 600.00,
            "status": "SUCCESS"
        }
        response = self.client.post(self.webhook_url, payload, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_duplicate"] is False
        assert response.data["status"] == "success"

        self.booking.refresh_from_db()
        assert self.booking.status == Booking.Status.CONFIRMED
        assert Payment.objects.filter(transaction_id="txn_gateway_9999").exists()
        assert WebhookLog.objects.filter(event_id="evt_unique_1001").exists()

    def test_webhook_duplicate_delivery_is_idempotent(self):
        payload = {
            "event_id": "evt_duplicate_2002",
            "event_type": "payment.success",
            "booking_id": str(self.booking.id),
            "transaction_id": "txn_gateway_8888",
            "amount": 600.00,
            "status": "SUCCESS"
        }

        # First delivery
        response1 = self.client.post(self.webhook_url, payload, format='json')
        assert response1.status_code == status.HTTP_200_OK
        assert response1.data["is_duplicate"] is False

        initial_payment_count = Payment.objects.count()
        initial_webhook_count = WebhookLog.objects.count()

        # Duplicate delivery (Exact same payload & event_id sent again)
        response2 = self.client.post(self.webhook_url, payload, format='json')
        assert response2.status_code == status.HTTP_200_OK
        assert response2.data["is_duplicate"] is True
        assert response2.data["status"] == "already_processed"

        # Verify no duplicate payments or log corruption occurred
        assert Payment.objects.count() == initial_payment_count
        assert WebhookLog.objects.count() == initial_webhook_count

        self.booking.refresh_from_db()
        assert self.booking.status == Booking.Status.CONFIRMED

    def test_webhook_failed_status_updates_booking(self):
        payload = {
            "event_id": "evt_fail_3003",
            "event_type": "payment.failed",
            "booking_id": str(self.booking.id),
            "transaction_id": "txn_gateway_7777",
            "amount": 600.00,
            "status": "FAILED"
        }
        response = self.client.post(self.webhook_url, payload, format='json')
        assert response.status_code == status.HTTP_200_OK
        
        self.booking.refresh_from_db()
        assert self.booking.status == Booking.Status.FAILED

    def test_webhook_invalid_booking_id_returns_404(self):
        payload = {
            "event_id": "evt_invalid_4004",
            "event_type": "payment.success",
            "booking_id": "00000000-0000-0000-0000-000000000000",
            "transaction_id": "txn_gateway_0000",
            "status": "SUCCESS"
        }
        response = self.client.post(self.webhook_url, payload, format='json')
        assert response.status_code == status.HTTP_404_NOT_FOUND
