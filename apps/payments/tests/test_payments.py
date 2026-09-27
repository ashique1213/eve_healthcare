import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from apps.centres.models import DiagnosticCentre, DiagnosticTest, CentreTest
from apps.bookings.models import Booking
from apps.payments.models import Payment

User = get_user_model()


@pytest.mark.django_db
class TestSimulatedPayment:
    def setup_method(self):
        self.client = APIClient()
        self.patient = User.objects.create_user(
            username="pay_user",
            email="pay@test.com",
            password="Password123!",
            role=User.Role.PATIENT
        )
        self.other_patient = User.objects.create_user(
            username="other_user",
            email="other@test.com",
            password="Password123!",
            role=User.Role.PATIENT
        )
        self.centre = DiagnosticCentre.objects.create(name="City Diagnostic", location="Indiranagar", city="Bangalore", address="1st Main")
        self.test = DiagnosticTest.objects.create(name="Vitamin D", code="VIT-D-01")
        self.centre_test = CentreTest.objects.create(centre=self.centre, test=self.test, price=1500.00)
        
        self.booking = Booking.objects.create(
            user=self.patient,
            centre_test=self.centre_test,
            amount=1500.00,
            appointment_datetime=timezone.now() + timedelta(days=2),
            status=Booking.Status.PENDING
        )
        self.payment_url = reverse('payment-process')

    def test_simulated_payment_success(self):
        self.client.force_authenticate(user=self.patient)
        payload = {
            "booking_id": str(self.booking.id),
            "status": "SUCCESS",
            "payment_method": "CARD"
        }
        response = self.client.post(self.payment_url, payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['status'] == Payment.Status.SUCCESS
        
        self.booking.refresh_from_db()
        assert self.booking.status == Booking.Status.CONFIRMED

    def test_simulated_payment_failed(self):
        self.client.force_authenticate(user=self.patient)
        payload = {
            "booking_id": str(self.booking.id),
            "status": "FAILED",
            "payment_method": "UPI"
        }
        response = self.client.post(self.payment_url, payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['status'] == Payment.Status.FAILED

        self.booking.refresh_from_db()
        assert self.booking.status == Booking.Status.FAILED

    def test_payment_unauthorized_user_denied(self):
        self.client.force_authenticate(user=self.other_patient)
        payload = {
            "booking_id": str(self.booking.id),
            "status": "SUCCESS"
        }
        response = self.client.post(self.payment_url, payload, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_payment_invalid_booking_id(self):
        self.client.force_authenticate(user=self.patient)
        payload = {
            "booking_id": "00000000-0000-0000-0000-000000000000",
            "status": "SUCCESS"
        }
        response = self.client.post(self.payment_url, payload, format='json')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_payment_history_list(self):
        self.client.force_authenticate(user=self.patient)
        history_url = reverse('payment-history')
        response = self.client.get(history_url)
        assert response.status_code == status.HTTP_200_OK

        admin_user = User.objects.create_user(
            username="adminpay",
            email="adminpay@test.com",
            password="Password123!",
            role=User.Role.ADMIN
        )
        self.client.force_authenticate(user=admin_user)
        admin_response = self.client.get(history_url)
        assert admin_response.status_code == status.HTTP_200_OK

    def test_payment_already_confirmed_booking_rejected(self):
        self.booking.status = Booking.Status.CONFIRMED
        self.booking.save()

        self.client.force_authenticate(user=self.patient)
        payload = {
            "booking_id": str(self.booking.id),
            "status": "SUCCESS"
        }
        response = self.client.post(self.payment_url, payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already confirmed" in str(response.data)

    def test_payment_cancelled_booking_rejected(self):
        self.booking.status = Booking.Status.CANCELLED
        self.booking.save()

        self.client.force_authenticate(user=self.patient)
        payload = {
            "booking_id": str(self.booking.id),
            "status": "SUCCESS"
        }
        response = self.client.post(self.payment_url, payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "cancelled booking" in str(response.data)

    def test_payment_with_idempotency_key(self):
        self.client.force_authenticate(user=self.patient)
        payload = {
            "booking_id": str(self.booking.id),
            "status": "SUCCESS",
            "idempotency_key": "user_idemp_key_9999"
        }
        response1 = self.client.post(self.payment_url, payload, format='json')
        assert response1.status_code == status.HTTP_201_CREATED
        payment_id = response1.data['id']

        # Repeat payment with same idempotency key
        response2 = self.client.post(self.payment_url, payload, format='json')
        assert response2.status_code == status.HTTP_200_OK
        assert response2.data['id'] == payment_id
        assert Payment.objects.filter(idempotency_key="user_idemp_key_9999").count() == 1

    def test_payment_using_booking_reference(self):
        self.client.force_authenticate(user=self.patient)
        payload = {
            "booking_id": self.booking.booking_reference,
            "status": "SUCCESS"
        }
        response = self.client.post(self.payment_url, payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        self.booking.refresh_from_db()
        assert self.booking.status == Booking.Status.CONFIRMED

    def test_celery_notification_task(self):
        from apps.payments.tasks import send_booking_confirmation_notification
        result = send_booking_confirmation_notification(str(self.booking.id))
        assert "Notification sent" in result

    def test_celery_cleanup_expired_bookings(self):
        from apps.payments.tasks import cleanup_expired_pending_bookings
        # Create a stale booking
        stale_booking = Booking.objects.create(
            user=self.patient,
            centre_test=self.centre_test,
            amount=1500.00,
            appointment_datetime=timezone.now() + timedelta(days=2),
            status=Booking.Status.PENDING
        )
        # Mock created_at in the past
        Booking.objects.filter(id=stale_booking.id).update(created_at=timezone.now() - timedelta(hours=48))

        count = cleanup_expired_pending_bookings()
        assert count >= 1
        stale_booking.refresh_from_db()
        assert stale_booking.status == Booking.Status.FAILED


