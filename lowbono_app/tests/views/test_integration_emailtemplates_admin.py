import os
import time
from lowbono_app.models import User, EmailTemplates, EmailEventEnterState, EmailEventInactiveFor, EmailEventDeadline
from django.core import mail
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from splinter import Browser
from selenium.webdriver.firefox.service import Service

class EmailTemplateAdminFormIntegrationTest(StaticLiveServerTestCase):

    def setUp(self):
        self.staff_user = User.objects.create_superuser(email="c1@lowbono.org", password='testpassword')
        my_service = Service(env={'MOZ_HEADLESS': '1'})
        self.browser = Browser('firefox', service=my_service)
        # self.browser = Browser('chrome')

        self.login_url = self.live_server_url + reverse('login')
        self.logout_url = self.live_server_url + reverse('logout')
        self.template_add_url = self.live_server_url + reverse('admin:lowbono_app_emailtemplates_add')

        # Staff user logs in
        self.browser.visit(self.login_url)
        self.browser.fill('email', 'c1@lowbono.org')
        self.browser.fill('password', 'testpassword')
        self.browser.find_by_css('button[type=submit]').first.click()

        # workaround to fill body field via ckeditor iframe using splinter/selenium. just delete the CKEDITOR on body field, and simply insert a textarea element
        self.js_clear_ckeditor_body_field = 'document.querySelector(".django-ckeditor-widget").innerHTML = ""; var textarea = document.createElement("textarea"); textarea.name = "body"; document.querySelector(".django-ckeditor-widget").appendChild(textarea);'

    def tearDown(self):
        self.browser.quit()

    def test__add_email_template_fails_WHEN_workflow_type_IS_NOT_valid(self):
        self.browser.visit(self.template_add_url)

        self.browser.fill('description', 'test')
        self.browser.fill('subject', 'test')
        self.browser.execute_script(self.js_clear_ckeditor_body_field)
        self.browser.fill('body', 'test')
        self.browser.find_by_css("#id_recipient [value='PROFESSIONAL_EMAIL']").click()
        self.browser.find_by_css("#id_event_type [value='emailevententerstate']").click()
        self.browser.find_by_css('input[type=submit][name="_save"]').first.click()

        self.assertIn("Oops, please choose a valid workflow type", self.browser.html)

    def test__add_email_template_fails_WHEN_event_type_IS_NOT_valid(self):
        self.browser.visit(self.template_add_url)

        self.browser.fill('description', 'test')
        self.browser.fill('subject', 'test')
        self.browser.execute_script(self.js_clear_ckeditor_body_field)
        self.browser.fill('body', 'test')
        self.browser.find_by_css("#id_recipient [value='PROFESSIONAL_EMAIL']").click()

        option_ids = [] # available workflow model contenttype ids
        for option in self.browser.find_by_css("#id_workflow_type").first.find_by_tag('option'):
            if option.value.isdigit():
                option_ids.append(option.value)
        self.browser.find_by_css("#id_workflow_type [value='" + option_ids[-1] + "']").click() # choose a workflow
        time.sleep(3) # wait for it load into form by HTMX

        self.browser.find_by_css('input[type=submit][name="_save"]').first.click()

        self.assertIn("This field is required", self.browser.html)

    def test__add_email_template_emailevent_workflow_type_field_HAS_valid_choices_as_per_SELECTED_workflow_type(self):
        self.browser.visit(self.template_add_url)

        self.browser.fill('description', 'test')
        self.browser.fill('subject', 'test')
        self.browser.execute_script(self.js_clear_ckeditor_body_field)
        self.browser.fill('body', 'test')
        self.browser.find_by_css("#id_recipient [value='PROFESSIONAL_EMAIL']").click()

        option_ids = [] # available workflow model contenttype ids
        for option in self.browser.find_by_css("#id_workflow_type").first.find_by_tag('option'):
            if option.value.isdigit():
                option_ids.append(option.value)

        nodes = None
        if option_ids[-1]: # select last one
            nodes = ContentType.objects.get(pk=option_ids[-1]).model_class().pretty_nodes # get last one's pretty_fields

        self.browser.find_by_css("#id_workflow_type [value='" + option_ids[-1] + "']").click() # choose a workflow

        time.sleep(3) # wait for it load into form by HTMX
        self.assertIn(list(nodes.keys())[0], self.browser.html) # check if a node value exists in html i.e. it has appeared in inline select box


    def test__only_that_emailevent_IS_stored_which_IS_equivalent_of_event_type_field_on_template(self):

        template_count = EmailTemplates.objects.count()
        enterstate_count = EmailEventEnterState.objects.count()
        inactivefor_count = EmailEventInactiveFor.objects.count()

        self.browser.visit(self.template_add_url)
        self.browser.fill('description', 'test')
        self.browser.fill('subject', 'test')
        self.browser.execute_script(self.js_clear_ckeditor_body_field)
        self.browser.fill('body', 'test')
        self.browser.find_by_css("#id_recipient [value='PROFESSIONAL_EMAIL']").click()
        option_ids = [] # available workflow model contenttype ids
        for option in self.browser.find_by_css("#id_workflow_type").first.find_by_tag('option'):
            if option.value.isdigit():
                option_ids.append(option.value)
        self.browser.find_by_css("#id_workflow_type [value='" + option_ids[-1] + "']").click() # choose a workflow
        time.sleep(3) # wait for it load into form by HTMX

        # emailevententerstate is selected, and it's values are added
        self.browser.find_by_css("#id_event_type [value='emailevententerstate']").click()
        self.browser.find_by_css("#id_emailevententerstate-0-workflow_state [value='waiting_for_first_pre_consult_update']").click()
        self.browser.fill("emailevententerstate-0-days_after", 5)

        # however, now 'emaileventinactivefor' is selected, and it's values are filled
        self.browser.find_by_css("#id_event_type [value='emaileventinactivefor']").click()
        self.browser.find_by_css("#id_emaileventinactivefor-0-workflow_state [value='waiting_for_first_pre_consult_update']").click()
        self.browser.fill("emaileventinactivefor-0-days_inactive", 5)
        self.browser.find_by_css('input[type=submit][name="_save"]').first.click()

        self.assertEqual(enterstate_count, EmailEventEnterState.objects.count()) # EmailEventEnterState is same as earlier, despite filling
        self.assertEqual(inactivefor_count + 1, EmailEventInactiveFor.objects.count()) # EmailEventInactiveFor count increased
        self.assertEqual(template_count + 1, EmailTemplates.objects.count()) # EmailTemplates count increased
