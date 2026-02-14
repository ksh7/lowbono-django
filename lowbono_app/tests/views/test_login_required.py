from django.test import TestCase
from lowbono_app.tests.utils import create_user, create_practice_area, get_complete_kwargs, create_referral, create_vacation
from lowbono_app.models import User
from django.test import Client
from django.urls import reverse


class LoginRequiredViewsTestCase(TestCase):

    def setUp(self):
        user, _, _ = create_user('jdoe@example.com', password='testpass', **get_complete_kwargs())
        self.user = user
        self.referral = create_referral(self.user)
        self.vacation = create_vacation(self.user)
        self.client = Client()

    def tearDown(self):
        del self.user
        del self.client

    def test_dashboard_view_template(self):

        cut = reverse('dashboard')
        response = self.client.get(cut)

        expected = 302
        actual = response.status_code
        self.assertEqual(expected, actual)

    def test_invite_view_template(self):

        cut = reverse('invite')
        response = self.client.get(cut)

        expected = 302
        actual = response.status_code
        self.assertEqual(expected, actual)

    def test_referral_detail_with_id_view_template(self):

        cut = reverse('referral-detail', args=[self.referral.id])
        response = self.client.get(cut)

        expected = 302
        actual = response.status_code
        self.assertEqual(expected, actual)

    def test_referral_edit_with_id_view_template(self):

        cut = reverse('referral-update', args=[self.referral.id])
        response = self.client.get(cut)

        expected = 302
        actual = response.status_code
        self.assertEqual(expected, actual)

    def test_vacations_list_view_template(self):

        cut = reverse('vacations', args=[self.user.id])
        response = self.client.get(cut)

        expected = 302
        actual = response.status_code
        self.assertEqual(expected, actual)

    def test_vacation_add_with_user_id_view_template(self):

        cut = reverse('vacations-add', args=[self.user.id])
        response = self.client.get(cut)

        expected = 302
        actual = response.status_code
        self.assertEqual(expected, actual)

    def test_vacation_edit_with_user_id_view_template(self):

        cut = reverse('vacations-edit', args=[self.user.id, self.vacation.id])
        response = self.client.get(cut)

        expected = 302
        actual = response.status_code
        self.assertEqual(expected, actual)
