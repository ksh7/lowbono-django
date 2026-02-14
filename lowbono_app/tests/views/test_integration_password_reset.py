import os
from lowbono_app.models import User, EmailTemplates
from lowbono_lawyer.models import Lawyer
from django.core import mail
from django.urls import reverse
from django.test import TestCase
from splinter import Browser
from selenium.webdriver.firefox.service import Service

class PasswordResetIntegrationTest(TestCase):
    def setUp(self):
        self.test_user = User.objects.create_user(email="c5@lowbono.org", password='testpassword')
        self.lawyer = Lawyer(user=self.test_user)
        self.lawyer.save()

        self.browser = Browser('django')

    def tearDown(self):
        self.browser.quit()

    def test_attorney_password_reset(self):

        # Attorney user tries resetting password
        self.browser.visit(reverse('reset_password'))
        self.browser.fill('email', self.test_user.email)
        self.browser.find_by_css('button[type=submit]').first.click()
        self.assertIn("Password reset link email sent to " + self.test_user.email + " Please check your email inbox", self.browser.html)

        # Check if email is sent to the Attorney
        actual = self.test_user.email
        expected = mail.outbox[0].to
        self.assertIn(actual, expected)

        # Attorney user opens the link sent in the email and sees new password page
        self.browser.visit(self.test_user.token.get_absolute_url())
        self.assertIn("Please enter a new password.", self.browser.html)
        self.browser.fill('password', 'newtestpassword')
        self.browser.find_by_css('button[type=submit]').first.click()
        self.assertIn("Account created! Please login to access profile", self.browser.html)

        # Attorney user go to /login page and enter details
        self.browser.visit(reverse('login'))
        self.browser.fill('email', self.test_user.email)
        self.browser.fill('password', 'newtestpassword')
        self.browser.find_by_css('button[type=submit]').first.click()

        # Attorney user can visit profile details page after logging in
        self.browser.visit(reverse('user-detail', kwargs={'id': self.test_user.id}))
        self.assertIn("Attorney referrals are paused because your attorney profile is not complete.", self.browser.html)
        self.browser.visit(reverse('logout'))

