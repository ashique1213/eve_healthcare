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

