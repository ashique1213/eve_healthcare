import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from apps.centres.models import DiagnosticCentre, DiagnosticTest, CentreTest
from apps.bookings.models import Booking

User = get_user_model()


@pytest.mark.django_db
class TestBookingSystem:
    def setup_method(self):
        self.client = APIClient()
        self.patient1 = User.objects.create_user(
            username="patient1",
            email="patient1@test.com",
            password="Password123!",
            role=User.Role.PATIENT
        )
        self.patient2 = User.objects.create_user(
            username="patient2",
            email="patient2@test.com",
            password="Password123!",
            role=User.Role.PATIENT
        )
        self.admin = User.objects.create_user(
            username="admin_bk",
            email="admin_bk@test.com",
            password="Password123!",
            role=User.Role.ADMIN,
            is_staff=True
        )

        self.centre = DiagnosticCentre.objects.create(name="Central Lab", location="MG Road", city="Bangalore", address="123 Street")
        self.test = DiagnosticTest.objects.create(name="Lipid Profile", code="LIP-001")
        self.centre_test = CentreTest.objects.create(centre=self.centre, test=self.test, price=1200.00, is_available=True)
        self.booking_url = reverse('booking-list')

    def test_create_booking_success(self):
        self.client.force_authenticate(user=self.patient1)
        future_time = (timezone.now() + timedelta(days=3)).isoformat()
        payload = {
            "centre_test": str(self.centre_test.id),
            "appointment_datetime": future_time,
            "notes": "Fasting morning appointment"
        }
        response = self.client.post(self.booking_url, payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == Booking.Status.PENDING
        assert float(response.data["amount"]) == 1200.00
        assert "booking_reference" in response.data

    def test_create_booking_past_datetime_fails(self):
        self.client.force_authenticate(user=self.patient1)
        past_time = (timezone.now() - timedelta(days=1)).isoformat()
        payload = {
            "centre_test": str(self.centre_test.id),
            "appointment_datetime": past_time
        }
        response = self.client.post(self.booking_url, payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "appointment_datetime" in response.data

    def test_patient_can_only_see_own_bookings(self):
        # Create booking for patient1
        b1 = Booking.objects.create(
            user=self.patient1,
            centre_test=self.centre_test,
            amount=1200.00,
            appointment_datetime=timezone.now() + timedelta(days=2),
            status=Booking.Status.PENDING
        )
        # Create booking for patient2
        b2 = Booking.objects.create(
            user=self.patient2,
            centre_test=self.centre_test,
            amount=1200.00,
            appointment_datetime=timezone.now() + timedelta(days=2),
            status=Booking.Status.PENDING
        )

        self.client.force_authenticate(user=self.patient1)
        response = self.client.get(self.booking_url)
        assert response.status_code == status.HTTP_200_OK
        returned_ids = [item['id'] for item in response.data['results']]
        assert str(b1.id) in returned_ids
        assert str(b2.id) not in returned_ids

    def test_admin_can_see_all_bookings(self):
        b1 = Booking.objects.create(
            user=self.patient1,
            centre_test=self.centre_test,
            amount=1200.00,
            appointment_datetime=timezone.now() + timedelta(days=2)
        )
        b2 = Booking.objects.create(
            user=self.patient2,
            centre_test=self.centre_test,
            amount=1200.00,
            appointment_datetime=timezone.now() + timedelta(days=2)
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.booking_url)
        assert response.status_code == status.HTTP_200_OK
        returned_ids = [item['id'] for item in response.data['results']]
        assert str(b1.id) in returned_ids
        assert str(b2.id) in returned_ids

    def test_cancel_booking_success(self):
        booking = Booking.objects.create(
            user=self.patient1,
            centre_test=self.centre_test,
            amount=1200.00,
            appointment_datetime=timezone.now() + timedelta(days=2),
            status=Booking.Status.PENDING
        )
        self.client.force_authenticate(user=self.patient1)
        cancel_url = reverse('booking-cancel', kwargs={'pk': str(booking.id)})
        response = self.client.post(cancel_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['booking']['status'] == Booking.Status.CANCELLED
        booking.refresh_from_db()
        assert booking.status == Booking.Status.CANCELLED

    def test_booking_retrieve_and_update(self):
        booking = Booking.objects.create(
            user=self.patient1,
            centre_test=self.centre_test,
            amount=1200.00,
            appointment_datetime=timezone.now() + timedelta(days=2),
            status=Booking.Status.PENDING
        )
        self.client.force_authenticate(user=self.patient1)
        detail_url = reverse('booking-detail', kwargs={'pk': str(booking.id)})
        response = self.client.get(detail_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(booking.id)

        # Patch notes
        patch_response = self.client.patch(detail_url, {"notes": "Updated fasting note"}, format='json')
        assert patch_response.status_code == status.HTTP_200_OK

        # Other patient cannot view
        self.client.force_authenticate(user=self.patient2)
        forbidden_response = self.client.get(detail_url)
        assert forbidden_response.status_code == status.HTTP_403_FORBIDDEN

    def test_booking_delete(self):
        booking = Booking.objects.create(
            user=self.patient1,
            centre_test=self.centre_test,
            amount=1200.00,
            appointment_datetime=timezone.now() + timedelta(days=2),
            status=Booking.Status.PENDING
        )
        self.client.force_authenticate(user=self.patient1)
        detail_url = reverse('booking-detail', kwargs={'pk': str(booking.id)})
        response = self.client.delete(detail_url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Booking.objects.filter(id=booking.id).exists()

    def test_cancel_edge_cases(self):
        booking = Booking.objects.create(
            user=self.patient1,
            centre_test=self.centre_test,
            amount=1200.00,
            appointment_datetime=timezone.now() + timedelta(days=2),
            status=Booking.Status.CANCELLED
        )
        self.client.force_authenticate(user=self.patient1)
        cancel_url = reverse('booking-cancel', kwargs={'pk': str(booking.id)})
        response = self.client.post(cancel_url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Unauthorized cancel
        self.client.force_authenticate(user=self.patient2)
        response_unauth = self.client.post(cancel_url)
        assert response_unauth.status_code == status.HTTP_403_FORBIDDEN

    def test_create_booking_via_centre_id_and_test_id(self):
        self.client.force_authenticate(user=self.patient1)
        future_time = (timezone.now() + timedelta(days=4)).isoformat()
        payload = {
            "centre_id": str(self.centre.id),
            "test_id": str(self.test.id),
            "appointment_datetime": future_time,
            "notes": "Direct IDs booking"
        }
        response = self.client.post(self.booking_url, payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert float(response.data["amount"]) == 1200.00
        assert response.data["status"] == Booking.Status.PENDING

    def test_create_booking_invalid_combination_fails(self):
        self.client.force_authenticate(user=self.patient1)
        future_time = (timezone.now() + timedelta(days=4)).isoformat()
        payload = {
            "centre_id": "00000000-0000-0000-0000-000000000000",
            "test_id": str(self.test.id),
            "appointment_datetime": future_time
        }
        response = self.client.post(self.booking_url, payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cancel_failed_booking_rejected(self):
        booking = Booking.objects.create(
            user=self.patient1,
            centre_test=self.centre_test,
            amount=1200.00,
            appointment_datetime=timezone.now() + timedelta(days=2),
            status=Booking.Status.FAILED
        )
        self.client.force_authenticate(user=self.patient1)
        cancel_url = reverse('booking-cancel', kwargs={'pk': str(booking.id)})
        response = self.client.post(cancel_url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot cancel a failed booking" in response.data["error"]

    def test_booking_detail_not_found(self):
        self.client.force_authenticate(user=self.patient1)
        detail_url = reverse('booking-detail', kwargs={'pk': "00000000-0000-0000-0000-000000000000"})
        response = self.client.get(detail_url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cancel_booking_not_found(self):
        self.client.force_authenticate(user=self.patient1)
        cancel_url = reverse('booking-cancel', kwargs={'pk': "00000000-0000-0000-0000-000000000000"})
        response = self.client.post(cancel_url)
        assert response.status_code == status.HTTP_404_NOT_FOUND


