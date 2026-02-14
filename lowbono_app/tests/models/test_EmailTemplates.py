from django.test import TestCase
from django import forms
from django.apps import apps
from lowbono_app.models import EmailTemplates
from django.contrib.admin import site
from lowbono_app.models import User, Referral, ReferralSource
from lowbono_lawyer.workflows import ReferralLawyerWorkflowState


class EmailTemplatesTestCase(TestCase):

    def setUp(self):
        self._workflow_ct = apps.get_model('contenttypes', 'ContentType').objects.filter(app_label='lowbono_lawyer', model='referrallawyerworkflowstate').first()
        self.template_data = {'description': 'test', 'subject': 'subject', 'body': 'body', 'recipient': 'PROFESSIONAL_EMAIL',
                              'workflow_type': '', 'event_type': ''}

    def tearDown(self):
        del self.template_data

    def test__raise_value_error_WHEN_workflow_type_field_IS_empty(self):
        with self.assertRaises(ValueError) as e:
            _, _ = EmailTemplates.objects.create(**self.template_data)

        self.assertIn('"EmailTemplates.workflow_type" must be a "ContentType" instance', str(e.exception))

    def test__raise_value_error_WHEN_workflow_type_field_IS_NOT_contenttype_instance(self):
        self.template_data['workflow_type'] = 'referralworkflow'
        with self.assertRaises(ValueError) as e:
            _, _ = EmailTemplates.objects.create(**self.template_data)

        self.assertIn('must be a "ContentType" instance', str(e.exception))

    def test__emailtemplate_object_created_WHEN_workflow_type_field_IS_contenttype_instance(self):
        cut = EmailTemplates.objects.count()
        self.template_data['workflow_type'] = self._workflow_ct
        EmailTemplates.objects.create(**self.template_data)
        actual = EmailTemplates.objects.count()

        self.assertEqual(cut + 1, actual)


class EmailTemplatesAdminFormTestCase(TestCase):

    def setUp(self):
        self._workflow_ct = apps.get_model('contenttypes', 'ContentType').objects.filter(app_label='lowbono_lawyer', model='referrallawyerworkflowstate').first()
        self.data = {'description': 'test', 'subject': 'subject', 'body': 'body', 'recipient': 'PROFESSIONAL_EMAIL', 'workflow_type': '', 'event_type': ''}

    def tearDown(self):
        del self.data

    def test__admin_emailtemplate_modelform_submission_IS_invalid_WHEN_workflow_type_AND_event_type_values_IS_invalid(self):
        self.data['workflow_type'] = ''
        self.data['event_type'] = ''
        form_class = site._registry[EmailTemplates].get_form(request=None) # get django admin EmailTemplates form class
        cut = form_class(data=self.data)

        actual = cut.is_valid()
        self.assertFalse(actual)

    def test__admin_emailtemplate_modelform_submission_IS_invalid_WHEN_workflow_type_value_IS_invalid(self):
        self.data['workflow_type'] = ''
        self.data['event_type'] = 'emailevententerstate'
        form_class = site._registry[EmailTemplates].get_form(request=None) # get django admin EmailTemplates form class
        cut = form_class(data=self.data)

        actual = cut.is_valid()
        self.assertFalse(actual)

    def test__admin_emailtemplate_modelform_submission_IS_invalid_WHEN_event_type_value_IS_invalid(self):
        self.data['workflow_type'] = self._workflow_ct
        self.data['event_type'] = ''
        form_class = site._registry[EmailTemplates].get_form(request=None) # get django admin EmailTemplates form class
        cut = form_class(data=self.data)

        actual = cut.is_valid()
        self.assertFalse(actual)

    def test__admin_emailtemplate_modelform_submission_IS_valid_WHEN_workflow_type_AND_event_type_values_IS_valid(self):
        self.data['workflow_type'] = self._workflow_ct
        self.data['event_type'] = 'emailevententerstate'
        form_class = site._registry[EmailTemplates].get_form(request=None) # get django admin EmailTemplates form class
        cut = form_class(data=self.data)

        actual = cut.is_valid()
        self.assertTrue(actual)
