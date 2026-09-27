import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from apps.centres.models import DiagnosticCentre, DiagnosticTest, CentreTest

User = get_user_model()


@pytest.mark.django_db
class TestDiagnosticCentresAndTests:
    def setup_method(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_user(
            username="admin_test",
            email="admin@test.com",
            password="Password123!",
            role=User.Role.ADMIN,
            is_staff=True
        )
        self.patient_user = User.objects.create_user(
            username="patient_test",
            email="patient@test.com",
            password="Password123!",
            role=User.Role.PATIENT
        )
        self.centre = DiagnosticCentre.objects.create(
            name="Apollo Centre",
            location="Indiranagar",
            city="Bangalore",
            address="100 Feet Rd"
        )
        self.test = DiagnosticTest.objects.create(
            name="Complete Blood Count",
            code="CBC-100",
            category="Blood",
            description="Full blood count"
        )
        self.centre_test = CentreTest.objects.create(
            centre=self.centre,
            test=self.test,
            price=500.00,
            is_available=True
        )

    def test_public_can_list_centres(self):
        url = reverse('diagnostic-centres-list')
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
        assert response.data['results'][0]['name'] == "Apollo Centre"

    def test_search_centres(self):
        url = reverse('diagnostic-centres-list') + "?search=Indiranagar"
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1

    def test_patient_cannot_create_centre(self):
        url = reverse('diagnostic-centres-list')
        self.client.force_authenticate(user=self.patient_user)
        payload = {
            "name": "Unauthorized Centre",
            "location": "Downtown",
            "city": "Mumbai",
            "address": "Street 1"
        }
        response = self.client.post(url, payload, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_create_centre(self):
        url = reverse('diagnostic-centres-list')
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "name": "New Admin Centre",
            "location": "Whitefield",
            "city": "Bangalore",
            "address": "ITPL Main Rd"
        }
        response = self.client.post(url, payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert DiagnosticCentre.objects.filter(name="New Admin Centre").exists()

    def test_admin_can_create_centre_test_price(self):
        url = reverse('centre-tests-list')
        self.client.force_authenticate(user=self.admin_user)
        new_test = DiagnosticTest.objects.create(name="LFT", code="LFT-200")
        payload = {
            "centre": str(self.centre.id),
            "test": str(new_test.id),
            "price": "750.00",
            "is_available": True
        }
        response = self.client.post(url, payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert CentreTest.objects.filter(centre=self.centre, test=new_test).exists()

    def test_retrieve_and_update_centre(self):
        detail_url = reverse('diagnostic-centres-detail', kwargs={'pk': str(self.centre.id)})
        response = self.client.get(detail_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(self.centre.id)

        # Admin update
        self.client.force_authenticate(user=self.admin_user)
        patch_res = self.client.patch(detail_url, {"location": "Koramangala"}, format='json')
        assert patch_res.status_code == status.HTTP_200_OK
        assert patch_res.data['location'] == "Koramangala"

        # Admin delete
        del_res = self.client.delete(detail_url)
        assert del_res.status_code == status.HTTP_204_NO_CONTENT

    def test_diagnostic_test_crud(self):
        list_url = reverse('diagnostic-tests-list')
        response = self.client.get(list_url)
        assert response.status_code == status.HTTP_200_OK

        detail_url = reverse('diagnostic-tests-detail', kwargs={'pk': str(self.test.id)})
        detail_res = self.client.get(detail_url)
        assert detail_res.status_code == status.HTTP_200_OK

        # Admin create test
        self.client.force_authenticate(user=self.admin_user)
        create_res = self.client.post(list_url, {"name": "Thyroid", "code": "THY-01", "category": "Hormones"}, format='json')
        assert create_res.status_code == status.HTTP_201_CREATED

        # Admin update test
        update_res = self.client.patch(detail_url, {"name": "Updated CBC"}, format='json')
        assert update_res.status_code == status.HTTP_200_OK

        # Admin delete test
        del_res = self.client.delete(detail_url)
        assert del_res.status_code == status.HTTP_204_NO_CONTENT

    def test_centre_test_detail_and_delete(self):
        detail_url = reverse('centre-tests-detail', kwargs={'pk': str(self.centre_test.id)})
        response = self.client.get(detail_url)
        assert response.status_code == status.HTTP_200_OK

        self.client.force_authenticate(user=self.admin_user)
        patch_res = self.client.patch(detail_url, {"price": "600.00"}, format='json')
        assert patch_res.status_code == status.HTTP_200_OK

        del_res = self.client.delete(detail_url)
        assert del_res.status_code == status.HTTP_204_NO_CONTENT

