from django.test import TestCase
from django.apps import apps
from lowbono_app.models import EmailTemplates, EmailEventEnterState, EmailEventInactiveFor, EmailEventDeadline


class EmailEventsTestCase(TestCase):

    def setUp(self):
        self._workflow_ct = apps.get_model('contenttypes', 'ContentType').objects.filter(app_label='lowbono_lawyer', model='referrallawyerworkflowstate').first()
        self.template_obj = EmailTemplates.objects.create(description='test', subject='subject', body='body', recipient='PROFESSIONAL_EMAIL', workflow_type=self._workflow_ct, event_type='')

    def tearDown(self):
        pass

    def test__emailevententerstate_object_IS_NOT_saved_IF_template_object_event_type_IS_NOT_equalto_emailevententerstate(self):
        self.template_obj.event_type = ''
        self.template_obj.save()
        cut = EmailEventEnterState.objects.count()

        EmailEventEnterState.objects.create(workflow_state='waiting_for_pre_consult_update', days_after=0, template=self.template_obj)
        actual = EmailEventEnterState.objects.count()
        self.assertEqual(cut, actual)

    def test__emailevententerstate_object_IS_saved_IF_template_object_event_type_IS_equalto_emailevententerstate(self):
        self.template_obj.event_type = 'emailevententerstate'
        self.template_obj.save()
        cut = EmailEventEnterState.objects.count()

        EmailEventEnterState.objects.create(workflow_state='waiting_for_pre_consult_update', days_after=0, template=self.template_obj)
        actual = EmailEventEnterState.objects.count()
        self.assertEqual(cut + 1, actual)

    def test__emaileventinactivefor_object_IS_NOT_saved_IF_template_object_event_type_IS_NOT_equalto_emaileventinactivefor(self):
        self.template_obj.event_type = ''
        self.template_obj.save()
        cut = EmailEventInactiveFor.objects.count()

        EmailEventInactiveFor.objects.create(workflow_state='waiting_for_pre_consult_update', days_inactive=0, template=self.template_obj)
        actual = EmailEventInactiveFor.objects.count()
        self.assertEqual(cut, actual)

    def test__emaileventinactivefor_object_IS_saved_IF_template_object_event_type_IS_equalto_emaileventinactivefor(self):
        self.template_obj.event_type = 'emaileventinactivefor'
        self.template_obj.save()
        cut = EmailEventInactiveFor.objects.count()

        EmailEventInactiveFor.objects.create(workflow_state='waiting_for_pre_consult_update', days_inactive=0, template=self.template_obj)
        actual = EmailEventInactiveFor.objects.count()
        self.assertEqual(cut + 1, actual)

    def test__emaileventdeadline_object_IS_NOT_saved_IF_template_object_event_type_IS_NOT_equalto_emaileventdeadline(self):
        self.template_obj.event_type = ''
        self.template_obj.save()
        cut = EmailEventDeadline.objects.count()

        EmailEventDeadline.objects.create(workflow_state='waiting_for_pre_consult_update', before_or_after_deadline="+", days=1, template=self.template_obj)
        actual = EmailEventDeadline.objects.count()
        self.assertEqual(cut, actual)

    def test__emaileventdeadline_object_IS_saved_IF_template_object_event_type_IS_equalto_emaileventdeadline(self):
        self.template_obj.event_type = 'emaileventdeadline'
        self.template_obj.save()
        cut = EmailEventDeadline.objects.count()

        EmailEventDeadline.objects.create(workflow_state='waiting_for_pre_consult_update', before_or_after_deadline="+", days=1, template=self.template_obj)
        actual = EmailEventDeadline.objects.count()
        self.assertEqual(cut + 1, actual)
