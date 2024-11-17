from unittest.mock import patch

from django.conf import settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import User


class UserRegistrationTestCase(APITestCase):
    fixtures = ["users"]

    def test_user_registration(self):
        url = reverse("token_register")
        data = {
            "first_name": "Alice",
            "last_name": "Johnson",
            "email": "new.alice@example.com",
            "password": "password123",
        }
        response = self.client.post(url, data, format="json")

        # Assert the registration is successful
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert that a user was created in the database
        self.assertTrue(User.objects.filter(email=data["email"]).exists())

        # Assert JWT tokens are returned
        self.assertIn("refresh", response.data)
        self.assertIn("access", response.data)

    def test_invalid_registration(self):
        url = reverse("token_register")
        data = {
            "first_name": "Alice",
            "last_name": "Johnson",
            "email": "alice.johnson@example.com",
            # Password missing
        }
        response = self.client.post(url, data, format="json")

        # Assert the registration fails due to missing fields
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_email_registration(self):
        url = reverse("token_register")
        data = {
            "first_name": "Alice",
            "last_name": "Johnson",
            "email": "john.doe@example.com",  # Existing email
            "password": "password123",
        }
        response = self.client.post(url, data, format="json")

        # Assert the registration fails due to duplicate email
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserLoginTestCase(APITestCase):
    fixtures = ["users"]

    def test_user_login(self):
        url = reverse("login_user")
        data = {"email": "john.doe@example.com", "password": "your_password"}
        response = self.client.post(url, data, format="json")

        # Assert that login is successful
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert JWT tokens are returned
        self.assertIn("refresh", response.data)
        self.assertIn("access", response.data)

    def test_invalid_login(self):
        url = reverse("login_user")
        data = {"email": "john.doe@example.com", "password": "wrongpassword"}
        response = self.client.post(url, data, format="json")

        # Assert that login failed
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_unregistered_email(self):
        url = reverse("login_user")
        data = {"email": "unregistered@example.com", "password": "password123"}
        response = self.client.post(url, data, format="json")

        # Assert that login failed due to unregistered email
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserListTestCase(APITestCase):
    fixtures = ["users"]

    def setUp(self):
        # Authenticate with user John
        self.client.force_authenticate(user=User.objects.get(pk=1))

    def test_user_list_pagination(self):
        url = reverse("user_list")
        response = self.client.get(url, {"page": 1})

        # Assert that the user list request is successful and paginated
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertIn("count", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)

    def test_user_list(self):
        url = reverse("user_list")
        response = self.client.get(url)

        # Assert that the user list request is successful
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert that the user is in the returned list
        self.assertGreaterEqual(len(response.data), 1)
        self.assertEqual(response.data["results"][0]["full_name"], "John Doe")

    def test_user_list_unauthenticated(self):
        self.client.logout()
        url = reverse("user_list")
        response = self.client.get(url)

        # Assert that the user list request is forbidden for unauthenticated users
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class GitHubLoginRedirectViewTestCase(APITestCase):
    def test_github_login_redirect(self):
        url = reverse("github_login_redirect")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, settings.GITHUB_AUTH_REDIRECT)


class GithubAuthCallbackViewTestCase(APITestCase):
    def setUp(self):
        self.url = reverse("github_auth_callback")

    @patch("apps.users.views.SocialLoginView.post")
    def test_github_auth_callback_with_valid_code(self, mock_post):
        mock_post.return_value.status_code = 200
        response = self.client.get(self.url, {"code": "valid_code"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("refresh", response.data)
        self.assertIn("access", response.data)
        mock_post.assert_called_once()

    @patch("apps.users.views.SocialLoginView.post")
    def test_github_auth_callback_with_invalid_code(self, mock_post):
        mock_post.return_value.status_code = 400
        response = self.client.get(self.url, {"code": "invalid_code"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data, {"detail": "Failed to authenticate with GitHub"}
        )

    def test_github_auth_callback_without_code(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, {"detail": "No authorization code provided"})
