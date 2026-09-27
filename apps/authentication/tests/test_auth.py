import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


@pytest.mark.django_db
class TestAuthentication:
    def setup_method(self):
        self.client = APIClient()
        self.register_url = reverse('auth-register')
        self.login_url = reverse('auth-login')
        self.profile_url = reverse('auth-profile')

    def test_user_signup_success(self):
        payload = {
            "username": "newpatient",
            "email": "patient@example.com",
            "password": "Password123!",
            "password_confirm": "Password123!",
            "first_name": "Jane",
            "last_name": "Doe",
            "phone_number": "+1234567890"
        }
        response = self.client.post(self.register_url, payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert "user" in response.data
        assert response.data["user"]["username"] == "newpatient"
        assert User.objects.filter(username="newpatient").exists()

    def test_user_signup_password_mismatch(self):
        payload = {
            "username": "mismatch",
            "email": "mismatch@example.com",
            "password": "Password123!",
            "password_confirm": "DifferentPassword123!",
            "first_name": "Test",
            "last_name": "User"
        }
        response = self.client.post(self.register_url, payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in response.data

    def test_user_login_success(self):
        user = User.objects.create_user(
            username="loginuser",
            email="login@example.com",
            password="SecurePassword123!"
        )
        payload = {
            "username": "loginuser",
            "password": "SecurePassword123!"
        }
        response = self.client.post(self.login_url, payload, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data
        assert response.data["user"]["username"] == "loginuser"

    def test_user_login_invalid_credentials(self):
        User.objects.create_user(
            username="wrongpassuser",
            email="wrongpass@example.com",
            password="CorrectPassword123!"
        )
        payload = {
            "username": "wrongpassuser",
            "password": "WrongPassword123!"
        }
        response = self.client.post(self.login_url, payload, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_profile_access(self):
        user = User.objects.create_user(
            username="profileuser",
            email="profile@example.com",
            password="Password123!"
        )
        self.client.force_authenticate(user=user)
        response = self.client.get(self.profile_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == "profileuser"

    def test_unauthenticated_profile_access_denied(self):
        response = self.client.get(self.profile_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_profile_put_update(self):
        user = User.objects.create_user(
            username="updateuser",
            email="update@example.com",
            password="Password123!",
            first_name="OldName"
        )
        self.client.force_authenticate(user=user)
        payload = {
            "username": "updateuser",
            "email": "update@example.com",
            "first_name": "NewName",
            "last_name": "User"
        }
        response = self.client.put(self.profile_url, payload, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data["first_name"] == "NewName"
        user.refresh_from_db()
        assert user.first_name == "NewName"

    def test_authenticated_profile_patch_update(self):
        user = User.objects.create_user(
            username="patchuser",
            email="patch@example.com",
            password="Password123!"
        )
        self.client.force_authenticate(user=user)
        payload = {"first_name": "PatchedName"}
        response = self.client.patch(self.profile_url, payload, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data["first_name"] == "PatchedName"
        user.refresh_from_db()
        assert user.first_name == "PatchedName"

