import random
from django.test import TestCase, override_settings
from splinter import Browser
from datetime import date, timedelta
from .. import models
from .. import constants

from unittest.mock import patch

steps = (
    ('1', {'data': {'in_dc': 'True'}, 'click': 'Submit', 'expect': {'step': 2}},),
)


class StepsTestCase(TestCase):
    fixtures = ['admin-user', 'group-permissions', 'sample-data-temp'] #, 'pages', 'cms-sites', 'cms-plugins',]

    def setUp(self):
        self.browser = Browser('django')
    
    def assertAtUrl(self, url):
        self.assertEqual(url, self.browser.url)

    def assertAtStep(self, step):
        self.assertAtUrl(f'/lawyers/{step}')

    def assertTextPresent(self, text):
        self.assertTrue(self.browser.is_text_present(text))

    def assertTextNotPresent(self, text):
        self.assertFalse(self.browser.is_text_present(text))

    def visit(self, url):
        self.browser.visit(url)
    
    def fill_form(self, field_values, form_id=None, name=None, ignore_missing=False):
        self.browser.fill_form(field_values, form_id=None, name=None, ignore_missing=False)

    def click(self, name=None, text=None, value=None):
        if name:
            self.browser.find_by_name(name).click()
        elif text is not None:
            self.browser.find_by_text(text).click()
        elif value is not None:
            self.browser.find_by_value(str(value)).click()

    def get_referral_by_email(self, email):
        return models.Referral.objects.get(email=email)
        
    def test_step_1_WHEN_select_dc_EXPECT_step_2(self):
        self.visit('/lawyers/1')
        self.fill_form({'in_dc': 'True'})
        self.click(text='Continue')
        self.assertAtStep(2)

    def test_step_1_WHEN_select_elsewhere_EXPECT_step_1_error(self):
        self.visit('/lawyers/1')
        self.fill_form({'in_dc': 'False'})
        self.click(text='Continue')
        
        self.assertAtStep(1)
        self.assertTextPresent('Outside coverage area')

    def test_step_2_WHEN_request_qualify_check_EXPECT_step_3(self):
        self.visit('/lawyers/1')
        self.click(text='Continue')

        self.click(text="I want to see if I qualify")
        self.assertAtStep(3)

    def test_step_2_WHEN_skip_qualify_check_EXPECT_step_4(self):
        self.visit('/lawyers/1')
        self.click(text='Continue')

        self.click(text="skip")
        self.assertAtStep(4)

    def test_step_3_WHEN_enter_low_income_EXPECT_step_3_low_income(self):
        self.visit('/lawyers/1')
        self.click(text='Continue')
        self.click(text="I want to see if I qualify")
        
        self.assertAtStep(3)
        self.fill_form({'household_size': '1', 'monthly_income': str(constants.FIRST_HOUSEHOLD_MEMBER_POVERTY_RATE/12)})
        self.click(text='Update estimate')
        self.assertAtStep(3)
        self.assertTextPresent('free legal assistance')

    def test_step_3_WHEN_enter_qualifying_income_EXPECT_step_3_qualifying_income(self):
        self.visit('/lawyers/1')
        self.click(text='Continue')
        self.click(text="I want to see if I qualify")
        
        self.assertAtStep(3)
        self.fill_form({'household_size': '1', 'monthly_income': str(3 * constants.FIRST_HOUSEHOLD_MEMBER_POVERTY_RATE / 12)})
        self.click(text='Update estimate')
        self.assertAtStep(3)
        self.assertTextPresent('reduced rates')

    def test_step_3_WHEN_enter_high_income_EXPECT_step_3_high_income(self):
        self.visit('/lawyers/1')
        self.click(text='Continue')
        self.click(text="I want to see if I qualify")
        
        self.assertAtStep(3)
        self.fill_form({'household_size': '1', 'monthly_income': str(5 * constants.FIRST_HOUSEHOLD_MEMBER_POVERTY_RATE / 12)})
        self.click(text='Update estimate')
        self.assertAtStep(3)
        self.assertTextPresent('market rates')

    def test_step_6_WHEN_click_practicearea_EXPECT_step_7(self):
        self.visit('/lawyers/1')
        self.click(text='Continue')
        self.click(text="skip")
        self.click(text="Continue without AI")

        self.assertAtStep(6)
        self.click(value=1) # select family
        self.assertAtStep(7)

    def test_step_7_WHEN_click_practicearea_with_attorneys_EXPECT_step_8(self):
        self.visit('/lawyers/1')
        self.click(text='Continue')
        self.click(text="skip")
        self.click(text="Continue without AI")
        self.click(value=1) # select family

        self.assertAtStep(7)
        self.click(value=1) # select name change
        self.assertAtStep(8)

    def test_step_7_WHEN_click_practicearea_without_attorneys_EXPECT_step_7_error(self):
        self.visit('/lawyers/1')
        self.click(text='Continue')
        self.click(text="skip")
        self.click(text="Continue without AI")
        self.click(value=1) # select family

        self.assertAtStep(7)
        self.click(value=3) # select Child Guardianship
        self.assertAtStep(7)
        self.assertTextPresent('We are sorry, there are no lawyers in the LowBono network who match your search.')

    def test_step_8_WHEN_click_skip_EXPECT_step_9(self):
        self.visit('/lawyers/1')
        self.click(text='Continue')
        self.click(text="skip")
        self.click(text="Continue without AI")
        self.click(value=1) # select family
        self.click(value=1) # select name change

        self.assertAtStep(8)
        self.click(text="skip")
        self.assertAtStep(9)

    def test_step_8_WHEN_choose_deadline_date_equal_or_more_than_today_EXPECT_step_9(self):
        self.visit('/lawyers/1')
        self.click(text='Continue')
        self.click(text="skip")
        self.click(text="Continue without AI")
        self.click(value=1) # select family
        self.click(value=1) # select name change

        self.assertAtStep(8)
        self.fill_form({'deadline_date': str(date.today() + timedelta(days=random.randint(0, 10)))})
        self.click(text='Add & Continue')
        self.assertAtStep(9)

    def test_step_8_WHEN_choose_deadline_date_less_than_today_EXPECT_step_8_error(self):
        self.visit('/lawyers/1')
        self.click(text='Continue')
        self.click(text="skip")
        self.click(text="Continue without AI")
        self.click(value=1) # select family
        self.click(value=1) # select name change

        self.assertAtStep(8)
        self.fill_form({'deadline_date': str(date.today() - timedelta(days=2))})
        self.click(text='Add & Continue')
        self.assertAtStep(8)
        self.assertTextPresent('cannot choose a past date')

    def test_step_9_WHEN_click_skip_EXPECT_step_10(self):
        self.visit('/lawyers/1')
        self.click(text='Continue')
        self.click(text="skip")
        self.click(text="Continue without AI")
        self.click(value=1) # select family
        self.click(value=1) # select name change
        self.click(text="skip")

        self.assertAtStep(9)
        self.click(text="skip")
        self.assertAtStep(10)

    def test_step_10_WHEN_click_select_lawyer_EXPECT_step_11(self):
        self.visit('/lawyers/1')
        self.click(text='Continue')
        self.click(text="skip")
        self.click(text="Continue without AI")
        self.click(value=1) # select family
        self.click(value=1) # select name change
        self.click(text="skip")
        self.click(text="skip")

        self.assertAtStep(10)
        self.click(text="Select Lawyer")
        self.assertAtStep(11)


    def test_step_11_WHEN_click_select_lawyer_skipping_previous_steps_EXPECT_step_12_with_nones(self):
        self.visit('/lawyers/1')
        self.click(text='Continue')
        self.click(text="skip")
        self.click(text="Continue without AI")
        self.click(value=1) # select family
        self.click(value=1) # select name change
        self.click(text="skip")
        self.click(text="skip")
        self.click(text="Select Lawyer")

        self.assertAtStep(11)
        self.fill_form({
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'jdoe@example.com',
            'phone': '202-555-5555',
            'address': '20006',
            'language': 'en',
            'contact_preference': True,
            'follow_up_consent': True,
            'referred_by': "3",
        })
        self.click(text='Request a consultation')

        self.assertAtStep(12)
        referral = self.get_referral_by_email('jdoe@example.com')

        # attorney info present
        self.assertTextPresent(referral.professional.first_name)

        # too soon date warning not present
        self.assertTextNotPresent('We encourage you to directly')
        
        # income info should all be none, since skipped
        self.assertIsNone(referral.monthly_income)
        self.assertIsNone(referral.household_size)
        self.assertIsNone(referral.income_status)

        # deadline info should be none, since skipped
        self.assertIsNone(referral.deadline_date)
        self.assertIsNone(referral.deadline_reason)

        # issue description should be none, since skipped
        self.assertEqual(referral.issue_description, "")

    def test_step_11_WHEN_click_select_lawyer_no_skipping_previous_steps_EXPECT_step_12_with_all_data(self):
        self.visit('/lawyers/1')
        self.click(text='Continue')

        self.click(text="I want to see if I qualify")
        monthly_income = 3 * constants.FIRST_HOUSEHOLD_MEMBER_POVERTY_RATE / 12
        self.fill_form({'household_size': '1', 'monthly_income': str(monthly_income)})
        self.click(text="Update estimate")
        self.click(text='Continue')
        self.click(text="Continue without AI") # but skipping LLM

        self.click(value=1) # select family
        self.click(value=1) # select name change
        self.fill_form({'deadline_date': '3000-01-01', 'deadline_reason': 'Court hearing'})
        self.click(text="Add & Continue")
        self.fill_form({'issue_description': 'lorem ipsum'})
        self.click(text="Add & Continue")
        self.click(text="Select Lawyer")

        self.assertAtStep(11)
        self.fill_form({
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'jdoe@example.com',
            'phone': '202-555-5555',
            'address': '20006',
            'language': 'en',
            'contact_preference': True,
            'follow_up_consent': True,
            'referred_by': "3",
        })
        self.click(text='Request a consultation')

        self.assertAtStep(12)
        referral = self.get_referral_by_email('jdoe@example.com')

        # too soon date warning not present
        self.assertTextNotPresent('We encourage you to directly')
        
        # income info should exist, since entered
        self.assertEqual(monthly_income, referral.monthly_income)
        self.assertEqual(1, referral.household_size)
        self.assertEqual('moderate', referral.income_status)

        # deadline info should exist, since entered
        self.assertEqual(date(3000, 1, 1), referral.deadline_date)
        self.assertEqual('Court hearing', referral.deadline_reason)

        # issue description should exist, since entered
        self.assertEqual('lorem ipsum', referral.issue_description)

    # LLM step tests
    def test_step_4_WHEN_click_consent_EXPECT_step_5(self):
        self.visit('/lawyers/1')
        self.click(text='Continue')
        self.click(text="skip")

        self.assertAtStep(4)
        self.click(text="I consent")
        self.assertAtStep(5)
        self.assertTextPresent('describe your legal issue')

    def test_step_5_WHEN_submit_issue_EXPECT_await_llm(self):
        self.visit('/lawyers/1')
        self.click(text='Continue')
        self.click(text="skip")
        self.click(text="I consent")

        self.assertAtStep(5)
        self.fill_form({'issue_description': 'lorem ipsum'})
        with patch('lowbono_app.tasks.llm_categorize_description.delay') as mock_task:
            mock_task.return_value.task_id = 'fake_task_id'
            self.click(text='Add & Continue')
            self.assertAtUrl('/lawyers/llm_await')
            self.assertTrue(mock_task.called)
