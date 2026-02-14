from django.test import TestCase
from django.test import Client
from django.urls import reverse

from lowbono_app.models import User, Token
from lowbono_lawyer.models import Lawyer
from lowbono_app.tests.utils import create_user, create_user_via_invite, get_complete_kwargs


class SignUpLoginFlowTestCase(TestCase):

    def setUp(self):
        User.objects.create_superuser('admin@example.com', 'testpass')
        self.client = Client()

    def tearDown(self):
        del self.client

    def test_invite_view_WHEN_adding_lawyer_EXPECT_user_and_lawyer_token_created_and_redirect_to_lawyers_view(self):

        self.client.login(email='admin@example.com', password='testpass')

        data = {
            "email": "jondoe@example.com",
            "first_name": "Jon",
            "last_name": " Doe",
            "profile_type": "lawyer",
        }

        cut = reverse('invite')

        response = self.client.post(cut, data=data)

        expected = 2
        actual = User.objects.count()
        self.assertEqual(expected, actual)

        expected = 1
        actual = Lawyer.objects.count()
        self.assertEqual(expected, actual)

        expected = 1
        actual = Token.objects.count()
        self.assertEqual(expected, actual)

        expected = reverse('professional-list')
        actual = response
        self.assertRedirects(actual, expected)

    def test_invite_view_WHEN_inviting_user_with_same_email_EXPECT_no_redirect_to_professionals_list_view_and_user_count_not_changed(self):

        self.client.login(email='admin@example.com', password='testpass')

        data = {
            "email": "jondoe@example.com",
            "first_name": "Jon",
            "last_name": " Doe",
            "profile_type": "lawyer",
        }

        cut = reverse('invite')
        response = self.client.post(cut, data=data)
        response = self.client.post(cut, data=data)  # try create new user with same data

        expected = 200
        actual = response.status_code
        self.assertEqual(expected, actual)

        expected = 2
        actual = User.objects.count()
        self.assertEqual(expected, actual)

    def test_signup_view_WHEN_invite_token_is_valid_EXPECT_ok_response(self):

        user = create_user_via_invite("jondoe@example.com")
        token = user.token.token

        cut = reverse('signup', args=[token])

        response = self.client.get(cut)

        expected = 200
        actual = response.status_code
        self.assertEqual(expected, actual)

    def test_signup_view_WHEN_invite_code_is_invalid_EXPECT_redirect_to_root(self):

        cut = reverse('signup', args=['random-token'])

        response = self.client.get(cut)

        expected = 302
        actual = response.status_code
        self.assertEqual(expected, actual)

        expected = '/'
        actual = response
        self.assertRedirects(actual, expected)

    def test_signup_view_WHEN_invite_code_is_valid_and_password_is_created_EXPECT_redirect_to_login(self):
        data = {
            "password": "123456"
        }

        user = create_user_via_invite("jondoe@example.com", data["password"])
        token = user.token.token

        cut = reverse('signup', args=[token])
        response = self.client.post(cut, data=data)

        expected = 302
        actual = response.status_code
        self.assertEqual(expected, actual)

        expected = reverse('login')
        actual = response
        self.assertRedirects(actual, expected)

    def test_login_view_WHEN_user_logs_in_first_time_EXPECT_redirect_to_user_update_view(self):
        data = {
            "email": "jondoe@example.com",
            "password": "123456"
        }

        user = create_user_via_invite(data["email"], data["password"])

        cut = reverse('login')
        response = self.client.post(cut, data=data)

        expected = 302
        actual = response.status_code
        self.assertEqual(expected, actual)

        expected = reverse('user-update', args=[user.id])
        actual = response
        self.assertRedirects(actual, expected)

    def test_login_view_WHEN_user_logs_in_2nd_time_EXPECT_redirect_to_dashboard_view(self):
        data = {
            "email": "jondoe@example.com",
            "password": "123456"
        }

        user = create_user_via_invite(data["email"], data["password"])

        cut = reverse('login')
        response = self.client.post(cut, data=data)

        expected = 302
        actual = response.status_code
        self.assertEqual(expected, actual)

        expected = reverse('user-update', args=[user.id])
        actual = response
        self.assertRedirects(actual, expected)

        response = self.client.post(reverse('logout'))

        response = self.client.post(cut, data=data)

        expected = 302
        actual = response.status_code
        self.assertEqual(expected, actual)

        expected = reverse('user-matters', args=[user.id])
        actual = response
        self.assertRedirects(actual, expected)
