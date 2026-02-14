import os
from lowbono_app.models import User
from django.core import mail
from django.urls import reverse
from django.test import LiveServerTestCase
from splinter import Browser
from selenium.webdriver.firefox.service import Service


class AttorneyOnboardIntegrationTest(LiveServerTestCase):

    def setUp(self):
        self.staff_user = User.objects.create_superuser(email="c1@lowbono.org", password='testpassword')
        my_service = Service(env={'MOZ_HEADLESS': '1'})
        self.browser = Browser('firefox', service=my_service)

        self.login_url = self.live_server_url + reverse('login')
        self.invite_url = self.live_server_url + reverse('invite')
        self.logout_url = self.live_server_url + reverse('logout')

    def tearDown(self):
        self.browser.quit()

    def test_attorney_onboard(self):

        # Staff user logs in
        self.browser.visit(self.login_url)
        self.browser.fill('email', 'c1@lowbono.org')
        self.browser.fill('password', 'testpassword')
        self.browser.find_by_css('button[type=submit]').first.click()

        # Access /invite page and invite user and logs out
        self.browser.visit(self.invite_url)
        self.browser.fill('email', 'a1@lowbono.com')
        self.browser.fill('first_name', 'test')
        self.browser.fill('last_name', 'user')
        self.browser.find_by_css('input[type=radio][value=lawyer]').first.click()
        self.browser.find_by_css('button[type=submit]').first.click()
        self.assertIn("Invitation to test user sent successfully!", self.browser.html)
        self.browser.visit(self.logout_url)

        # Check if email is sent to the user
        actual = 'a1@lowbono.com'
        expected = mail.outbox[0].to
        self.assertIn(actual, expected)

        self.attorney_user = User.objects.filter(email='a1@lowbono.com').first()

        # Attorney user opens the link sent in the email and sees new password page
        invitation_link = self.live_server_url  + self.attorney_user.token.get_absolute_url()
        self.browser.visit(invitation_link)
        self.assertIn("Please enter a new password.", self.browser.html)

        # Attorney user setup password on the signup page
        self.browser.fill('password', 'newtestpassword')
        self.browser.find_by_css('button[type=submit]').first.click()
        self.assertIn("Account created! Please login to access profile", self.browser.html)

        # Attorney user go to /login page and enter details
        self.browser.visit(self.login_url)
        self.browser.fill('email', 'a1@lowbono.com')
        self.browser.fill('password', 'newtestpassword')
        self.browser.find_by_css('button[type=submit]').first.click()

        # Attorney user first login redirects to profile edit page
        self.assertIn("Edit Basic Details", self.browser.html)

        # Attorney user visits profile details page and sees a warning
        self.profile_view_url = self.live_server_url  + reverse('user-detail', kwargs={'id': self.attorney_user.id})
        self.browser.visit(self.profile_view_url)
        self.assertIn("Referrals are paused because your profile is not complete.", self.browser.html)

        # Attorney user goes to profile edit page and fill all columns and save
        self.profile_edit_url = self.live_server_url  + reverse('user-update', kwargs={'id': self.attorney_user.id})
        self.browser.visit(self.profile_edit_url)

        self.browser.fill('firm_name', 'Firm ABC')
        self.test_image_path = os.path.join(os.path.dirname(__file__), 'test_data', 'sample.png')
        self.browser.attach_file('photo', self.test_image_path)
        self.browser.fill('email', 'A1@LOWBONO.com')
        self.browser.fill('phone', '2015550123')
        self.browser.fill('address', 'Test New York')
        self.browser.fill('bio', 'Test Bio')
        # checks a practice area
        self.browser.find_by_css('input[name=lawyer_user-0-practice_areas]').first.check()
        # clicks bar admission Add button and fills details
        self.browser.find_by_id('id_bar_admissions_add_btn').first.click()
        self.browser.select('bar_admissions-0-state', 'NY')
        self.browser.fill('bar_admissions-0-admission_date', '2023-01-01')
        self.browser.find_by_css('button[type=submit]').first.click()
        self.assertNotIn("Referrals are paused because your profile is not complete.", self.browser.html)
        self.assertNotIn("A1@LOWBONO.com", self.browser.html)
        self.assertIn("a1@lowbono.com", self.browser.html)
        self.browser.visit(self.logout_url)

        # Attorney user logs in again and gets redirected to referrals list page
        self.browser.visit(self.login_url)
        self.browser.fill('email', 'a1@lowbono.com')
        self.browser.fill('password', 'newtestpassword')
        self.browser.find_by_css('button[type=submit]').first.click()
        self.assertIn("All Referral Matters", self.browser.html)
        self.assertNotIn("Referrals are paused because your profile is not complete.", self.browser.html)
        self.browser.visit(self.logout_url)
