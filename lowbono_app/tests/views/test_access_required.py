from django.test import TestCase
from lowbono_app.tests.utils import create_user, create_practice_area, get_complete_kwargs, create_referral, create_vacation
from lowbono_app.models import User
from django.test import Client
from django.urls import reverse


class ViewsTestCase(TestCase):

    def setUp(self):
        user, _, _ = create_user('jdoe@example.com', password='testpass', **get_complete_kwargs())
        user2, _, _ = create_user('jdoe2@example.com', password='testpass', **get_complete_kwargs())
        self.user = user
        self.user2 = user2
        self.referral = create_referral(self.user)
        self.referral2 = create_referral(user2, email='sample2@gmail.com')
        self.vacation = create_vacation(self.user)
        self.client = Client()

    def tearDown(self):
        del self.user
        del self.client
    
    def test_user_view_with_unauthorized_user_id_view_template(self):

        self.client.login(email='jdoe@example.com', password='testpass')

        cut = reverse('user-detail', args=[self.user2.id])
        response = self.client.get(cut)

        expected = 302
        actual = response.status_code
        self.assertEqual(expected, actual)

    def test_user_edit_with_unauthorized_user_id_view_template(self):

        self.client.login(email='jdoe@example.com', password='testpass')

        cut = reverse('user-update', args=[self.user2.id])
        response = self.client.get(cut)

        expected = 302
        actual = response.status_code
        self.assertEqual(expected, actual)
    
    def test_referral_detail_view_with_unauthorized_user_view_template(self):

        self.client.login(email='jdoe@example.com', password='testpass')

        cut = reverse('referral-detail', args=[self.referral2.id])
        response = self.client.get(cut)

        expected = 302
        actual = response.status_code
        self.assertEqual(expected, actual)
    
    def test_referral_edit_with_unauthorized_user_view_template(self):

        self.client.login(email='jdoe@example.com', password='testpass')

        cut = reverse('referral-update', args=[self.referral2.id])
        response = self.client.get(cut)

        expected = 302
        actual = response.status_code
        self.assertEqual(expected, actual)
    
    def test_vacation_detail_view_with_unauthorized_user_id_view_template(self):

        self.client.login(email='jdoe@example.com', password='testpass')

        cut = reverse('vacations', args=[self.user2.id])
        response = self.client.get(cut)

        expected = 302
        actual = response.status_code
        self.assertEqual(expected, actual)
