from django.test import TestCase
from lowbono_app.tests.utils import create_user, create_practice_area, get_complete_kwargs, create_referral, create_vacation
from lowbono_app.models import User
from lowbono_lawyer.workflows import ReferralLawyerWorkflowState
from django.test import Client
from django.urls import reverse


class ViewsTestCase(TestCase):

    def setUp(self):
        user, _, _ = create_user('jdoe@example.com', password='testpass', **get_complete_kwargs())
        self.user = user
        self.referral = create_referral(self.user)
        self.vacation = create_vacation(self.user)
        self.client = Client()

    def tearDown(self):
        del self.user
        del self.client

    def test_login_view_template(self):

        cut = reverse('login')
        response = self.client.get(cut)

        expected = 200
        actual = response.status_code
        self.assertEqual(expected, actual)

        expected = 'lowbono_app/login.html'
        actual = response
        self.assertTemplateUsed(actual, expected)

    def test_logout_view_template(self):

        cut = reverse('logout')
        response = self.client.get(cut)

        expected = 302
        actual = response.status_code
        self.assertEqual(expected, actual)

    def test_dashboard_view_template(self):

        self.client.login(email='jdoe@example.com', password='testpass')

        cut = reverse('dashboard')
        response = self.client.get(cut)

        expected = 200
        actual = response.status_code
        self.assertEqual(expected, actual)

        expected = 'lowbono_app/dashboard.html'
        actual = response
        self.assertTemplateUsed(actual, expected)

    def test_invite_view_template(self):

        self.client.login(email='jdoe@example.com', password='testpass')

        cut = reverse('invite')
        response = self.client.get(cut)

        expected = 200
        actual = response.status_code
        self.assertEqual(expected, actual)

        expected = 'lowbono_app/user_invite_form.html'
        actual = response
        self.assertTemplateUsed(actual, expected)

    def test_signup_with_token_view_template(self):

        cut = reverse('signup', args=['token'])
        response = self.client.get(cut)

        expected = 302
        actual = response.status_code
        self.assertEqual(expected, actual)

        expected = '/'
        actual = response
        self.assertRedirects(actual, expected)

    def test_user_detail_with_user_id_view_template(self):

        self.client.login(email='jdoe@example.com', password='testpass')

        cut = reverse('user-detail', args=[self.user.id])
        response = self.client.get(cut)

        expected = 200
        actual = response.status_code
        self.assertEqual(expected, actual)

        expected = 'lowbono_app/user_detail.html'
        actual = response
        self.assertTemplateUsed(actual, expected)

    def test_go_step_view_template(self):

        cut = reverse('lawyer_step', args=[1])
        response = self.client.get(cut)

        expected = 200
        actual = response.status_code
        self.assertEqual(expected, actual)

        expected = 'steps/default.html'
        actual = response
        self.assertTemplateUsed(actual, expected)

    def test_professional_list_view_template(self):

        self.client.login(email='jdoe@example.com', password='testpass')

        cut = reverse('professional-list')
        response = self.client.get(cut)

        expected = 200
        actual = response.status_code
        self.assertEqual(expected, actual)

        expected = 'lowbono_app/professional_list.html'
        actual = response
        self.assertTemplateUsed(actual, expected)

    def test_referral_edit_with_id_view_template(self):

        self.client.login(email='jdoe@example.com', password='testpass')

        cut = reverse('referral-update', args=[self.referral.id])
        response = self.client.get(cut)

        expected = 200
        actual = response.status_code
        self.assertEqual(expected, actual)

        expected = 'lowbono_app/referral_update_form.html'
        actual = response
        self.assertTemplateUsed(actual, expected)

    def test_vacations_list_view_template(self):

        self.client.login(email='jdoe@example.com', password='testpass')

        cut = reverse('vacations', args=[self.user.id])
        response = self.client.get(cut)

        expected = 200
        actual = response.status_code
        self.assertEqual(expected, actual)

        expected = 'lowbono_app/vacation_list.html'
        actual = response
        self.assertTemplateUsed(actual, expected)

    def test_vacation_add_with_user_id_view_template(self):

        self.client.login(email='jdoe@example.com', password='testpass')

        cut = reverse('vacations-add', args=[self.user.id])
        response = self.client.get(cut)

        expected = 200
        actual = response.status_code
        self.assertEqual(expected, actual)

        expected = 'lowbono_app/vacation_create_form.html'
        actual = response
        self.assertTemplateUsed(actual, expected)

    def test_vacation_edit_with_user_id_view_template(self):

        self.client.login(email='jdoe@example.com', password='testpass')

        cut = reverse('vacations-edit', args=[self.user.id, self.vacation.id])
        response = self.client.get(cut)

        expected = 200
        actual = response.status_code
        self.assertEqual(expected, actual)

        expected = 'lowbono_app/vacation_update_form.html'
        actual = response
        self.assertTemplateUsed(actual, expected)
