import datetime
from django.core import mail
from django.apps import apps
from django.utils import timezone
from django.test import TestCase

from unittest.mock import patch

from lowbono.celery import app as celeryapp
from lowbono_app.models import User, Referral, ReferralSource, EmailTemplates, CeleryETATasks
from lowbono_lawyer.workflows import ReferralLawyerWorkflowState
from lowbono_mediator.workflows import ReferralMediatorWorkflowState
import inspect


class WorkflowLawyerEmailsTestCase(TestCase):
    def setUp(self):
        celeryapp.conf.update(CELERY_TASK_ALWAYS_EAGER=True)
        celeryapp.conf.update(CELERY_TASK_STORE_EAGER_RESULT=True)

        self.professional = User.objects.create(email='a1@dcerefer.org', password='password')
        self.referral_source = ReferralSource.objects.create(source='DC Affordable Law Firm')

    def test__lawyer__send_three_initial_notification_emails_sent_IF_referral_has_NO_deadline(self):
        self.referral = Referral.objects.create(professional=self.professional, email='test1@client.com', referred_by=self.referral_source)
        self.workflow = ReferralLawyerWorkflowState.referral_received(referral=self.referral)

        actual = len(mail.outbox)
        expected = 2
        self.assertEqual(actual, expected)

        # email 1
        actual = mail.outbox[0].subject
        expected = "You received a consultation request via LowBono.org"
        self.assertEqual(actual, expected)

        actual = self.referral.professional.email
        expected = mail.outbox[0].to
        self.assertIn(actual, expected)

        # email 2
        actual = mail.outbox[1].subject
        expected = "Your LowBono.org referral request"
        self.assertEqual(actual, expected)

        actual = self.referral.email
        expected = mail.outbox[1].to
        self.assertIn(actual, expected)

        # email 3: this is 4th day email, that will get delivered later on, but available in CeleryETATasks
        actual = CeleryETATasks.objects.count()
        expected = 1
        self.assertEqual(actual, expected)

        actual = CeleryETATasks.objects.all()[0].func
        expected = "emailtemplates_delayed_send_email"
        self.assertIn(actual, expected)

    def test__lawyer__celeryetatasks_function_and_args_ARE_available_in_tasks_module(self):
        from lowbono_app import tasks
        self.referral = Referral.objects.create(professional=self.professional, email='test1@client.com', referred_by=self.referral_source,
                                                deadline_date=datetime.datetime.now().date())
        self.workflow = ReferralLawyerWorkflowState.referral_received(referral=self.referral)

        # func name should be available in tasks.py
        func_name = CeleryETATasks.objects.first().func
        cut = hasattr(tasks, func_name)
        self.assertTrue(cut)

        # passed func args should same as task function args in tasks.py
        passed_args = set(CeleryETATasks.objects.first().args.keys())
        required_args = set(inspect.signature(getattr(tasks, func_name)).parameters.keys())
        self.assertEqual(passed_args, required_args)

    def test__lawyer__send_five_initial_notification_emails_sent_IF_referral_deadline_exists(self):
        self.referral = Referral.objects.create(professional=self.professional, email='test1@client.com', referred_by=self.referral_source,
                                                deadline_date=datetime.datetime.now().date())
        self.workflow = ReferralLawyerWorkflowState.referral_received(referral=self.referral)

        actual = len(mail.outbox)
        expected = 4
        self.assertEqual(actual, expected)

        # email 5: this is 4th day email, that will get delivered later on, but available in CeleryETATasks
        actual = CeleryETATasks.objects.count()
        expected = 1
        self.assertEqual(actual, expected)

    def test__lawyer__send_five_initial_notification_emails_sent_IF_referral_deadline_exists_AND_7_days_in_future(self):
        from lowbono_app.tasks import send_scheduled_eta_emails
        self.referral = Referral.objects.create(professional=self.professional, email='test1@client.com', referred_by=self.referral_source,
                                                deadline_date=datetime.datetime.now().date() + datetime.timedelta(days=9))
        self.workflow = ReferralLawyerWorkflowState.referral_received(referral=self.referral)

        actual = len(mail.outbox)
        expected = 2
        self.assertEqual(actual, expected)

        # another 3 emails: they will get delivered later on, but available in CeleryETATasks
        actual = CeleryETATasks.objects.count()
        expected = 3
        self.assertEqual(actual, expected)

    def test__lawyer__send_email_to_professional_AFTER_9th_day_of_last_update_WHEN_workflow_state_IS_waiting_for_first_pre_consult_update(self):
        from lowbono_app.tasks import send_scheduled_notification_emails
        self.referral = Referral.objects.create(professional=self.professional, email='test1@client.com', referred_by=self.referral_source)
        self.workflow = ReferralLawyerWorkflowState.referral_received(referral=self.referral)

        # email 3: this is 4th day email, that will get delivered later on, but available in CeleryETATasks
        actual = CeleryETATasks.objects.count()
        expected = 1
        self.assertEqual(actual, expected)

        actual = CeleryETATasks.objects.all()[0].func
        expected = "emailtemplates_delayed_send_email"
        self.assertIn(actual, expected)

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=5)):
            # email is not sent, if 9 days not passed
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox) # initial referral creation emails
            expected = 2
            self.assertEqual(actual, expected)

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=9)):
            # send email on 9th day
            send_scheduled_notification_emails() # run task

            actual = self.referral.professional.email
            expected = mail.outbox[2].to
            self.assertIn(actual, expected)

            actual = len(mail.outbox)
            expected = 3
            self.assertEqual(actual, expected)

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=15)):
            # email is not sent again, if 9 days not passed since last update
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 3
            self.assertEqual(actual, expected)

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=18)):
            # email is sent again, if atleast 9 days passed since last update
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 4
            self.assertEqual(actual, expected)

    def test__lawyer__send_email_to_professional_AFTER_30th_day_of_last_update_WHEN_workflow_state_IS_waiting_for_pre_consult_update(self):
        from lowbono_app.tasks import send_scheduled_notification_emails
        self.referral = Referral.objects.create(professional=self.professional, email='test1@client.com', referred_by=self.referral_source)
        self.workflow = ReferralLawyerWorkflowState.referral_received(referral=self.referral)
        self.task = self.workflow.task_set.latest()
        self.task.name = 'waiting_for_pre_consult_update'
        self.task.save(update_fields=['name'])

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=15)):
            # email is not sent, if 30 days not passed
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox) # initial referral creation emails
            expected = 2
            self.assertEqual(actual, expected)

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=30)):
            # send email on 30th day
            send_scheduled_notification_emails() # run task

            actual = self.referral.professional.email
            expected = mail.outbox[2].to
            self.assertIn(actual, expected)

            actual = len(mail.outbox)
            expected = 3
            self.assertEqual(actual, expected)

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=45)):
            # email is not sent again, if 30 days not passed since last update
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 3
            self.assertEqual(actual, expected)

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=60)):
            # email is sent again, if atleast 30 days passed since last update
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 4
            self.assertEqual(actual, expected)

    def test__lawyer__send_email_to_professional_AFTER_30th_day_of_last_update_WHEN_workflow_state_IS_waiting_for_post_consult_update(self):
        from lowbono_app.tasks import send_scheduled_notification_emails
        self.referral = Referral.objects.create(professional=self.professional, email='test1@client.com', referred_by=self.referral_source)
        self.workflow = ReferralLawyerWorkflowState.referral_received(referral=self.referral)
        self.task = self.workflow.task_set.latest()
        self.task.name = 'waiting_for_post_consult_update'
        self.task.save(update_fields=['name'])

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=15)):
            # email is not sent, if 30 days not passed
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox) # initial referral creation emails
            expected = 2
            self.assertEqual(actual, expected)

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=30)):
            # send email on 30th day
            send_scheduled_notification_emails() # run task

            actual = self.referral.professional.email
            expected = mail.outbox[2].to
            self.assertIn(actual, expected)

            actual = len(mail.outbox)
            expected = 3
            self.assertEqual(actual, expected)

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=45)):
            # email is not sent again, if 30 days not passed since last update
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 3
            self.assertEqual(actual, expected)

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=60)):
            # email is sent again, if atleast 30 days passed since last update
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 4
            self.assertEqual(actual, expected)

    def test__lawyer__send_email_to_professional_AFTER_90th_day_of_last_update_WHEN_workflow_state_IS_waiting_for_post_engagement_update(self):
        from lowbono_app.tasks import send_scheduled_notification_emails
        self.referral = Referral.objects.create(professional=self.professional, email='test1@client.com', referred_by=self.referral_source)
        self.workflow = ReferralLawyerWorkflowState.referral_received(referral=self.referral)
        self.task = self.workflow.task_set.latest()
        self.task.name = 'waiting_for_post_engagement_update'
        self.task.save(update_fields=['name'])

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=30)):
            # email is not sent, if 90 days not passed
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox) # initial referral creation emails
            expected = 2
            self.assertEqual(actual, expected)

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=90)):
            # send email on 90th day
            send_scheduled_notification_emails() # run task

            actual = self.referral.professional.email
            expected = mail.outbox[2].to
            self.assertIn(actual, expected)

            actual = len(mail.outbox)
            expected = 3
            self.assertEqual(actual, expected)

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=125)):
            # email is not sent again, if 90 days not passed since last update
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 3
            self.assertEqual(actual, expected)

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=180)):
            # email is sent again, if atleast 90 days passed since last update
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 4
            self.assertEqual(actual, expected)


class WorkflowMediatorEmailsTestCase(TestCase):
    def setUp(self):
        celeryapp.conf.update(CELERY_TASK_ALWAYS_EAGER=True)
        celeryapp.conf.update(CELERY_TASK_STORE_EAGER_RESULT=True)

        self.professional = User.objects.create(email='a1@dcerefer.org', password='password')
        self.referral_source = ReferralSource.objects.create(source='DC Affordable Law Firm')

    def test__mediator__send_three_initial_notification_emails_sent_IF_referral_has_NO_deadline(self):
        self.referral = Referral.objects.create(professional=self.professional, email='test1@client.com', referred_by=self.referral_source)
        self.workflow = ReferralMediatorWorkflowState.referral_received(referral=self.referral)

        actual = len(mail.outbox)
        expected = 2
        self.assertEqual(actual, expected)

        # email 1
        actual = mail.outbox[0].subject
        expected = "You received a consultation request via LowBono.org"
        self.assertEqual(actual, expected)

        actual = self.referral.professional.email
        expected = mail.outbox[0].to
        self.assertIn(actual, expected)

        # email 2
        actual = mail.outbox[1].subject
        expected = "Your LowBono.org referral request"
        self.assertEqual(actual, expected)

        actual = self.referral.email
        expected = mail.outbox[1].to
        self.assertIn(actual, expected)

        # email 3: this is 4th day email, that will get delivered later on, but available in CeleryETATasks
        actual = CeleryETATasks.objects.count()
        expected = 1
        self.assertEqual(actual, expected)

        actual = CeleryETATasks.objects.all()[0].func
        expected = "emailtemplates_delayed_send_email"
        self.assertIn(actual, expected)

    def test__mediator__celeryetatasks_function_and_args_ARE_available_in_tasks_module(self):
        from lowbono_app import tasks
        self.referral = Referral.objects.create(professional=self.professional, email='test1@client.com', referred_by=self.referral_source,
                                                deadline_date=datetime.datetime.now().date())
        self.workflow = ReferralMediatorWorkflowState.referral_received(referral=self.referral)

        # func name should be available in tasks.py
        func_name = CeleryETATasks.objects.first().func
        cut = hasattr(tasks, func_name)
        self.assertTrue(cut)

        # passed func args should same as task function args in tasks.py
        passed_args = set(CeleryETATasks.objects.first().args.keys())
        required_args = set(inspect.signature(getattr(tasks, func_name)).parameters.keys())
        self.assertEqual(passed_args, required_args)

    def test__mediator__send_five_initial_notification_emails_sent_IF_referral_deadline_exists(self):
        self.referral = Referral.objects.create(professional=self.professional, email='test1@client.com', referred_by=self.referral_source,
                                                deadline_date=datetime.datetime.now().date())
        self.workflow = ReferralMediatorWorkflowState.referral_received(referral=self.referral)

        actual = len(mail.outbox)
        expected = 4
        self.assertEqual(actual, expected)

        # email 5: this is 4th day email, that will get delivered later on, but available in CeleryETATasks
        actual = CeleryETATasks.objects.count()
        expected = 1
        self.assertEqual(actual, expected)

    def test__mediator__send_five_initial_notification_emails_sent_IF_referral_deadline_exists_AND_7_days_in_future(self):
        from lowbono_app.tasks import send_scheduled_eta_emails
        self.referral = Referral.objects.create(professional=self.professional, email='test1@client.com', referred_by=self.referral_source,
                                                deadline_date=datetime.datetime.now().date() + datetime.timedelta(days=9))
        self.workflow = ReferralMediatorWorkflowState.referral_received(referral=self.referral)

        actual = len(mail.outbox)
        expected = 2
        self.assertEqual(actual, expected)

        # another 3 emails: they will get delivered later on, but available in CeleryETATasks
        actual = CeleryETATasks.objects.count()
        expected = 3
        self.assertEqual(actual, expected)

    def test__mediator__send_email_to_professional_AFTER_9th_day_of_last_update_WHEN_workflow_state_IS_waiting_for_first_pre_consult_update(self):
        from lowbono_app.tasks import send_scheduled_notification_emails
        self.referral = Referral.objects.create(professional=self.professional, email='test1@client.com', referred_by=self.referral_source)
        self.workflow = ReferralMediatorWorkflowState.referral_received(referral=self.referral)

        # email 3: this is 4th day email, that will get delivered later on, but available in CeleryETATasks
        actual = CeleryETATasks.objects.count()
        expected = 1
        self.assertEqual(actual, expected)

        actual = CeleryETATasks.objects.all()[0].func
        expected = "emailtemplates_delayed_send_email"
        self.assertIn(actual, expected)

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=5)):
            # email is not sent, if 9 days not passed
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox) # initial referral creation emails
            expected = 2
            self.assertEqual(actual, expected)

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=9)):
            # send email on 9th day
            send_scheduled_notification_emails() # run task

            actual = self.referral.professional.email
            expected = mail.outbox[2].to
            self.assertIn(actual, expected)

            actual = len(mail.outbox)
            expected = 3
            self.assertEqual(actual, expected)

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=15)):
            # email is not sent again, if 9 days not passed since last update
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 3
            self.assertEqual(actual, expected)

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=18)):
            # email is sent again, if atleast 9 days passed since last update
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 4
            self.assertEqual(actual, expected)

    def test__mediator__send_email_to_professional_AFTER_30th_day_of_last_update_WHEN_workflow_state_IS_waiting_for_pre_consult_update_from_both_party(self):
        from lowbono_app.tasks import send_scheduled_notification_emails
        self.referral = Referral.objects.create(professional=self.professional, email='test1@client.com', referred_by=self.referral_source)
        self.workflow = ReferralMediatorWorkflowState.referral_received(referral=self.referral)
        self.task = self.workflow.task_set.latest()
        self.task.name = 'waiting_for_pre_consult_update_from_both_party'
        self.task.save(update_fields=['name'])

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=15)):
            # email is not sent, if 30 days not passed
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox) # initial referral creation emails
            expected = 2
            self.assertEqual(actual, expected)

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=30)):
            # send email on 30th day
            send_scheduled_notification_emails() # run task

            actual = self.referral.professional.email
            expected = mail.outbox[2].to
            self.assertIn(actual, expected)

            actual = len(mail.outbox)
            expected = 3
            self.assertEqual(actual, expected)

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=45)):
            # email is not sent again, if 30 days not passed since last update
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 3
            self.assertEqual(actual, expected)

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=60)):
            # email is sent again, if atleast 30 days passed since last update
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 4
            self.assertEqual(actual, expected)

    def test__mediator__send_email_to_professional_AFTER_30th_day_of_last_update_WHEN_workflow_state_IS_waiting_for_pre_consult_update_from_other_party(self):
        from lowbono_app.tasks import send_scheduled_notification_emails
        self.referral = Referral.objects.create(professional=self.professional, email='test1@client.com', referred_by=self.referral_source)
        self.workflow = ReferralMediatorWorkflowState.referral_received(referral=self.referral)
        self.task = self.workflow.task_set.latest()
        self.task.name = 'waiting_for_pre_consult_update_from_other_party'
        self.task.save(update_fields=['name'])

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=15)):
            # email is not sent, if 30 days not passed
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox) # initial referral creation emails
            expected = 2
            self.assertEqual(actual, expected)

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=30)):
            # send email on 30th day
            send_scheduled_notification_emails() # run task

            actual = self.referral.professional.email
            expected = mail.outbox[2].to
            self.assertIn(actual, expected)

            actual = len(mail.outbox)
            expected = 3
            self.assertEqual(actual, expected)

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=45)):
            # email is not sent again, if 30 days not passed since last update
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 3
            self.assertEqual(actual, expected)

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=60)):
            # email is sent again, if atleast 30 days passed since last update
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 4
            self.assertEqual(actual, expected)

    def test__mediator__send_email_to_professional_AFTER_30th_day_of_last_update_WHEN_workflow_state_IS_waiting_for_post_consult_update(self):
        from lowbono_app.tasks import send_scheduled_notification_emails
        self.referral = Referral.objects.create(professional=self.professional, email='test1@client.com', referred_by=self.referral_source)
        self.workflow = ReferralMediatorWorkflowState.referral_received(referral=self.referral)
        self.task = self.workflow.task_set.latest()
        self.task.name = 'waiting_for_post_consult_update'
        self.task.save(update_fields=['name'])

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=15)):
            # email is not sent, if 30 days not passed
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox) # initial referral creation emails
            expected = 2
            self.assertEqual(actual, expected)

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=30)):
            # send email on 30th day
            send_scheduled_notification_emails() # run task

            actual = self.referral.professional.email
            expected = mail.outbox[2].to
            self.assertIn(actual, expected)

            actual = len(mail.outbox)
            expected = 3
            self.assertEqual(actual, expected)

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=45)):
            # email is not sent again, if 30 days not passed since last update
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 3
            self.assertEqual(actual, expected)

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=60)):
            # email is sent again, if atleast 30 days passed since last update
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 4
            self.assertEqual(actual, expected)

    def test__mediator__send_email_to_professional_AFTER_90th_day_of_last_update_WHEN_workflow_state_IS_waiting_for_post_engagement_update(self):
        from lowbono_app.tasks import send_scheduled_notification_emails
        self.referral = Referral.objects.create(professional=self.professional, email='test1@client.com', referred_by=self.referral_source)
        self.workflow = ReferralMediatorWorkflowState.referral_received(referral=self.referral)
        self.task = self.workflow.task_set.latest()
        self.task.name = 'waiting_for_post_engagement_update'
        self.task.save(update_fields=['name'])

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=30)):
            # email is not sent, if 90 days not passed
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox) # initial referral creation emails
            expected = 2
            self.assertEqual(actual, expected)

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=90)):
            # send email on 90th day
            send_scheduled_notification_emails() # run task

            actual = self.referral.professional.email
            expected = mail.outbox[2].to
            self.assertIn(actual, expected)

            actual = len(mail.outbox)
            expected = 3
            self.assertEqual(actual, expected)

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=125)):
            # email is not sent again, if 90 days not passed since last update
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 3
            self.assertEqual(actual, expected)

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=180)):
            # email is sent again, if atleast 90 days passed since last update
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 4
            self.assertEqual(actual, expected)
