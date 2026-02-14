import datetime
import random
from django.core import mail
from django.apps import apps
from django.utils import timezone
from django.test import TestCase
from django.contrib.contenttypes.models import ContentType

from unittest.mock import patch

from lowbono.celery import app as celeryapp
from lowbono_app.models import User, Referral, ReferralSource, EmailTemplates, CeleryETATasks, EmailEventInactiveFor
from lowbono_lawyer.workflows import ReferralLawyerWorkflowState
from lowbono_mediator.workflows import ReferralMediatorWorkflowState
from lowbono_app.tasks import send_scheduled_notification_emails
import inspect


class LawyerInactiveAtFirstPreConsultTestCase(TestCase):
    """
        Test Case:
            professional: lawyer
            event_type: 'waiting_for_first_pre_consult_update'
            days_inactive: 9
    """

    def setUp(self):
        celeryapp.conf.update(CELERY_TASK_ALWAYS_EAGER=True)
        celeryapp.conf.update(CELERY_TASK_STORE_EAGER_RESULT=True)

        self.professional = User.objects.create(email='a1@dcerefer.org', password='password')
        self.referral_source = ReferralSource.objects.create(source='DC Affordable Law Firm')

        self.email_subject = 'Waiting For First Pre Consult Update'
        self._update_template_subject('waiting_for_first_pre_consult_update', ContentType.objects.get_for_model(ReferralLawyerWorkflowState), self.email_subject)

    def _update_template_subject(self, workflow_state, content_type, subject):
        """ set a custom email template subject"""

        event = EmailEventInactiveFor.objects.filter(workflow_state=workflow_state,
                                                     template__workflow_type=content_type).first()
        event.template.subject = subject # custom subject for testing
        event.template.save()

    def _create_referral_and_workflow(self):

        referral = Referral.objects.create(professional=self.professional, email='test1@client.com', referred_by=self.referral_source)
        workflow = ReferralLawyerWorkflowState.referral_received(referral=referral)
        mail.outbox = [] # clean initial email

        return referral, workflow

    def tearDown(self):
        mail.outbox = [] # clean initial email

    def test__NO_email_sent__BEFORE_9th_day__WHEN_workflow_state_IS_waiting_for_first_pre_consult_update(self):
        """ no email sent, if 9 days not passed """

        referral, workflow = self._create_referral_and_workflow()

        # day 8th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=8)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 0
            self.assertEqual(actual, expected)

    def test__send_email_to_professional__ON_9th_day__WHEN_workflow_state_IS_waiting_for_first_pre_consult_update(self):
        """ email sent, on 9th day """

        referral, workflow = self._create_referral_and_workflow()

        # day 9th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=9)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].to[0]
            expected = self.professional.email
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = self.email_subject
            self.assertEqual(actual, expected)
    
    def test__send_email_to_professional__AFTER_9th_day__WHEN_workflow_state_IS_waiting_for_first_pre_consult_update(self):
        """ email sent, even if task ran after 9th day i.e. say on 15th day """

        referral, workflow = self._create_referral_and_workflow()

        # day 15th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=15)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].to[0]
            expected = self.professional.email
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = self.email_subject
            self.assertEqual(actual, expected)

    def test__NO_email_sent__WHEN_lawyer_provides_human_update__BEFORE_9th_day__AT_waiting_for_first_pre_consult_update(self):
        """ email not sent on 9th day, if lawyer updated status on 6th day """
        
        referral, workflow = self._create_referral_and_workflow()

        # day 6th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=6)):
            workflow.hours_worked = 1
            workflow.save()

        # day 9th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=9)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 0
            self.assertEqual(actual, expected)

    def test__email_sent_again__WHEN_9_days_pass_AFTER_human_update__AT_waiting_for_first_pre_consult_update(self):
        """ email sent on 15th day, if lawyer updated status on 6th day i.e. 9 days after 6th day update """

        referral, workflow = self._create_referral_and_workflow()

        # day 6th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=6)):
            workflow.hours_worked = 1
            workflow.save()

        # day 15th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=15)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].to[0]
            expected = self.professional.email
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = self.email_subject
            self.assertEqual(actual, expected)


class LawyerInactiveAtPreConsultTestCase(TestCase):
    """
        Test Case:
            professional: lawyer
            event_type: 'waiting_for_pre_consult_update'
            days_inactive: 30
    """

    def setUp(self):
        celeryapp.conf.update(CELERY_TASK_ALWAYS_EAGER=True)
        celeryapp.conf.update(CELERY_TASK_STORE_EAGER_RESULT=True)

        self.professional = User.objects.create(email='a1@dcerefer.org', password='password')
        self.referral_source = ReferralSource.objects.create(source='DC Affordable Law Firm')

        self.email_subject = 'Waiting For Pre Consult Update'
        self._update_template_subject('waiting_for_pre_consult_update', ContentType.objects.get_for_model(ReferralLawyerWorkflowState), self.email_subject)

    def _update_template_subject(self, workflow_state, content_type, subject):
        """ set a custom email template subject"""

        event = EmailEventInactiveFor.objects.filter(workflow_state=workflow_state,
                                                     template__workflow_type=content_type).first()
        event.template.subject = subject # custom subject for testing
        event.template.save()

    def _create_referral_and_workflow(self):

        referral = Referral.objects.create(professional=self.professional, email='test1@client.com', referred_by=self.referral_source)
        workflow = ReferralLawyerWorkflowState.referral_received(referral=referral)
        mail.outbox = [] # clean initial email

        _next_node = workflow.get_node('waiting_for_pre_consult_update')
        workflow.task_set.all().latest().finish()
        workflow.task_set.all().latest().start_next_tasks([_next_node])
        workflow.save()

        return referral, workflow

    def tearDown(self):
        mail.outbox = [] # clean initial email

    def test__NO_email_sent__BEFORE_30th_day__WHEN_workflow_state_IS_waiting_for_pre_consult_update(self):
        """ no email sent, if 30 days not passed """

        referral, workflow = self._create_referral_and_workflow()

        # day 28th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=28)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 0
            self.assertEqual(actual, expected)

    def test__send_email_to_professional__ON_30th_day__WHEN_workflow_state_IS_waiting_for_pre_consult_update(self):
        """ email sent, on 30th day """

        referral, workflow = self._create_referral_and_workflow()

        # day 30th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=30)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].to[0]
            expected = self.professional.email
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = self.email_subject
            self.assertEqual(actual, expected)
    
    def test__send_email_to_professional__AFTER_30th_day__WHEN_workflow_state_IS_waiting_for_pre_consult_update(self):
        """ email sent, even if task ran after 30th day i.e. say on 40th day """

        referral, workflow = self._create_referral_and_workflow()

        # day 40th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=40)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].to[0]
            expected = self.professional.email
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = self.email_subject
            self.assertEqual(actual, expected)
    
    def test__NO_email_sent__WHEN_lawyer_provides_human_update__BEFORE_30th_day__AT_waiting_for_pre_consult_update(self):
        """ email not sent on 30th day, if lawyer updated status on 10th day """

        referral, workflow = self._create_referral_and_workflow()

        # day 10th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=10)):
            workflow.hours_worked = 1
            workflow.save()

        # day 30th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=30)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 0
            self.assertEqual(actual, expected)

    def test__email_sent_again__WHEN_30_days_pass_AFTER_human_update__AT_waiting_for_pre_consult_update(self):
        """ email sent on 40th day, if lawyer updated status on 10th day i.e. 30 days after 10th day update"""

        referral, workflow = self._create_referral_and_workflow()

        # day 10th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=10)):
            workflow.hours_worked = 1
            workflow.save()

        # day 40th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=40)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].to[0]
            expected = self.professional.email
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = self.email_subject
            self.assertEqual(actual, expected)


class LawyerInactiveAtPostConsultTestCase(TestCase):
    """
        Test Case:
            professional: lawyer
            event_type: 'waiting_for_post_consult_update'
            days_inactive: 30
    """

    def setUp(self):
        celeryapp.conf.update(CELERY_TASK_ALWAYS_EAGER=True)
        celeryapp.conf.update(CELERY_TASK_STORE_EAGER_RESULT=True)

        self.professional = User.objects.create(email='a1@dcerefer.org', password='password')
        self.referral_source = ReferralSource.objects.create(source='DC Affordable Law Firm')

        self.email_subject = 'Waiting For Post Consult Update'
        self._update_template_subject('waiting_for_post_consult_update', ContentType.objects.get_for_model(ReferralLawyerWorkflowState), self.email_subject)

    def _update_template_subject(self, workflow_state, content_type, subject):
        """ set a custom email template subject"""

        event = EmailEventInactiveFor.objects.filter(workflow_state=workflow_state,
                                                     template__workflow_type=content_type).first()
        event.template.subject = subject # custom subject for testing
        event.template.save()

    def _create_referral_and_workflow(self):

        referral = Referral.objects.create(professional=self.professional, email='test1@client.com', referred_by=self.referral_source)
        workflow = ReferralLawyerWorkflowState.referral_received(referral=referral)
        mail.outbox = [] # clean initial email

        _next_node = workflow.get_node('waiting_for_post_consult_update')
        workflow.task_set.all().latest().finish()
        workflow.task_set.all().latest().start_next_tasks([_next_node])
        workflow.save()

        return referral, workflow

    def tearDown(self):
        mail.outbox = [] # clean initial email

    def test__NO_email_sent__BEFORE_30th_day__WHEN_workflow_state_IS_waiting_for_post_consult_update(self):
        """ no email sent, if 30 days not passed """

        referral, workflow = self._create_referral_and_workflow()

        # day 28th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=28)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 0
            self.assertEqual(actual, expected)

    def test__send_email_to_professional__ON_30th_day__WHEN_workflow_state_IS_waiting_for_post_consult_update(self):
        """ email sent, on 30th day """

        referral, workflow = self._create_referral_and_workflow()

        # day 30th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=30)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].to[0]
            expected = self.professional.email
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = self.email_subject
            self.assertEqual(actual, expected)
    
    def test__send_email_to_professional__AFTER_30th_day__WHEN_workflow_state_IS_waiting_for_post_consult_update(self):
        """ email sent, even if task ran after 30th day i.e. say on 40th day """

        referral, workflow = self._create_referral_and_workflow()

        # day 40th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=40)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].to[0]
            expected = self.professional.email
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = self.email_subject
            self.assertEqual(actual, expected)

    def test__NO_email_sent__WHEN_lawyer_provides_human_update__BEFORE_30th_day__AT_waiting_for_post_consult_update(self):
        """ email not sent on 30th day, if lawyer updated status on 10th day """
        
        referral, workflow = self._create_referral_and_workflow()

        # day 10th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=10)):
            workflow.hours_worked = 1
            workflow.save()

        # day 30th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=30)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 0
            self.assertEqual(actual, expected)

    def test__email_sent_again__WHEN_30_days_pass_AFTER_human_update__AT_waiting_for_post_consult_update(self):
        """ email sent on 40th day, if lawyer updated status on 10th day i.e. 30 days after 10th day update"""

        referral, workflow = self._create_referral_and_workflow()

        # day 10th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=10)):
            workflow.hours_worked = 1
            workflow.save()

        # day 40th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=40)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].to[0]
            expected = self.professional.email
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = self.email_subject
            self.assertEqual(actual, expected)


class LawyerInactiveAtPostEngagementTestCase(TestCase):
    """
        Test Case:
            professional: lawyer
            event_type: 'waiting_for_post_engagement_update'
            days_inactive: 90
    """

    def setUp(self):
        celeryapp.conf.update(CELERY_TASK_ALWAYS_EAGER=True)
        celeryapp.conf.update(CELERY_TASK_STORE_EAGER_RESULT=True)

        self.professional = User.objects.create(email='a1@dcerefer.org', password='password')
        self.referral_source = ReferralSource.objects.create(source='DC Affordable Law Firm')

        self.email_subject = 'Waiting For Post Engagement Update'
        self._update_template_subject('waiting_for_post_engagement_update', ContentType.objects.get_for_model(ReferralLawyerWorkflowState), self.email_subject)

    def _update_template_subject(self, workflow_state, content_type, subject):
        """ set a custom email template subject"""

        event = EmailEventInactiveFor.objects.filter(workflow_state=workflow_state,
                                                     template__workflow_type=content_type).first()
        event.template.subject = subject # custom subject for testing
        event.template.save()

    def _create_referral_and_workflow(self):

        referral = Referral.objects.create(professional=self.professional, email='test1@client.com', referred_by=self.referral_source)
        workflow = ReferralLawyerWorkflowState.referral_received(referral=referral)
        mail.outbox = [] # clean initial email

        _next_node = workflow.get_node('waiting_for_post_engagement_update')
        workflow.task_set.all().latest().finish()
        workflow.task_set.all().latest().start_next_tasks([_next_node])
        workflow.save()

        return referral, workflow

    def tearDown(self):
        mail.outbox = [] # clean initial email

    def test__NO_email_sent__BEFORE_90th_day__WHEN_workflow_state_IS_waiting_for_post_engagement_update(self):
        """ no email sent, if 90 days not passed """

        referral, workflow = self._create_referral_and_workflow()

        # day 58th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=58)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 0
            self.assertEqual(actual, expected)

    def test__send_email_to_professional__ON_90th_day__WHEN_workflow_state_IS_waiting_for_post_engagement_update(self):
        """ email sent, on 90th day """

        referral, workflow = self._create_referral_and_workflow()

        # day 90th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=90)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].to[0]
            expected = self.professional.email
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = self.email_subject
            self.assertEqual(actual, expected)
    
    def test__send_email_to_professional__AFTER_90th_day__WHEN_workflow_state_IS_waiting_for_post_engagement_update(self):
        """ email sent, even if task ran after 90th day i.e. say on 110th day """

        referral, workflow = self._create_referral_and_workflow()

        # day 110th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=110)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].to[0]
            expected = self.professional.email
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = self.email_subject
            self.assertEqual(actual, expected)
    
    def test__NO_email_sent__WHEN_lawyer_provides_human_update__BEFORE_90th_day__AT_waiting_for_post_engagement_update(self):
        """ email not sent on 90th day, if lawyer updated status on 50th day """
        
        referral, workflow = self._create_referral_and_workflow()

        # day 50th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=50)):
            workflow.hours_worked = 1
            workflow.save()

        # day 90th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=90)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 0
            self.assertEqual(actual, expected)

    def test__email_sent_again__WHEN_90_days_pass_AFTER_human_update__AT_waiting_for_post_engagement_update(self):
        """ email sent on 140th day, if lawyer updated status on 50th day i.e. 90 days after 50th day update"""

        referral, workflow = self._create_referral_and_workflow()

        # day 50th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=50)):
            workflow.hours_worked = 1
            workflow.save()

        # day 140th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=140)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].to[0]
            expected = self.professional.email
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = self.email_subject
            self.assertEqual(actual, expected)


class SingleLawyerBulkEmailTestCase(TestCase):
    """
        Test Case:
            professional: single lawyer
            event_type: different workflow states
            email template: subject, body content 
    """

    def setUp(self):
        celeryapp.conf.update(CELERY_TASK_ALWAYS_EAGER=True)
        celeryapp.conf.update(CELERY_TASK_STORE_EAGER_RESULT=True)

        self.professional = User.objects.create(email='a1@dcerefer.org', password='password')
        self.referral_source = ReferralSource.objects.create(source='DC Affordable Law Firm')

        self._update_template_subject('waiting_for_first_pre_consult_update',
                                      ContentType.objects.get_for_model(ReferralLawyerWorkflowState),
                                      'Waiting For First Pre Consult Update',
                                      '{{OVERDUE_MATTERS_LIST|length}} overdue referrals')
        self._update_template_subject('waiting_for_pre_consult_update',
                                      ContentType.objects.get_for_model(ReferralLawyerWorkflowState),
                                      'Waiting For Pre Consult Update',
                                      '{{OVERDUE_MATTERS_LIST|length}} overdue referrals')

    def _update_template_subject(self, workflow_state, content_type, subject, body=''):
        """ set a custom email template subject"""

        event = EmailEventInactiveFor.objects.filter(workflow_state=workflow_state,
                                                     template__workflow_type=content_type).first()
        event.template.subject = subject # custom subject for testing
        event.template.body = body # custom subject for testing
        event.template.save()

    def _update_workflows_status(self, next_node, workflows=[]):
        for workflow in workflows:
            _next_node = workflow.get_node(next_node)
            workflow.task_set.all().latest().finish()
            workflow.task_set.all().latest().start_next_tasks([_next_node])
            workflow.save()

    def _create_multiple_referrals_and_workflows(self, count=1):
        referrals = []
        workflows = []
        for i in range(count):
            referral = Referral.objects.create(professional=self.professional, email=f'test{i+1}@example.com', referred_by=self.referral_source)
            workflow = ReferralLawyerWorkflowState.referral_received(referral=referral)
            referrals.append(referral)
            workflows.append(workflow) 

        mail.outbox = [] # clean initial email

        return referrals, workflows

    def tearDown(self):
        mail.outbox = [] # clean initial email

    def test__send_single_email_WITH_multiple_referrals_WHEN_multiple_referrals_overdue_FOR_same_professional__FOR_same_event_type(self):
        """ Multiple referrals for lawyer, however only 1 overdue email sent """

        _, workflows = self._create_multiple_referrals_and_workflows(10)

        # day 9th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=9)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = 'Waiting For First Pre Consult Update'
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].body
            expected = '10 overdue referrals'
            self.assertEqual(actual, expected)

    def test__send_separate_emails_WHEN_referrals_overdue_at_different_states_FOR_same_professional(self):
        """ Multiple referrals overdue at different states, however, for each state only 1 email sent """

        _, workflows = self._create_multiple_referrals_and_workflows(10)

        # update few referrals to 'waiting_for_pre_consult_update'
        self._update_workflows_status('waiting_for_pre_consult_update', random.sample(workflows, 4))

        # day 30th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=30)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 2
            self.assertEqual(actual, expected)

            # email 1
            actual = mail.outbox[0].subject
            expected = 'Waiting For First Pre Consult Update'
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].body
            expected = '6 overdue referrals'
            self.assertEqual(actual, expected)

            # email 2
            actual = mail.outbox[1].subject
            expected = 'Waiting For Pre Consult Update'
            self.assertEqual(actual, expected)

            actual = mail.outbox[1].body
            expected = '4 overdue referrals'
            self.assertEqual(actual, expected)

    def test__bulk_email_contains_only_overdue_referrals__WHEN_same_lawyer_has_overdue_and_non_overdue_referrals(self):
        """ in email, list only overdue emails, not the one recently updated """

        _, workflows = self._create_multiple_referrals_and_workflows(10)

        # update all referrals to 'waiting_for_pre_consult_update' at once, to use 30 days overdue schedule
        self._update_workflows_status('waiting_for_pre_consult_update', workflows)

        # day 20th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=20)):
            # update 4 random workflows
            self._update_workflows_status('waiting_for_pre_consult_update', random.sample(workflows, 4))

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=30)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = 'Waiting For Pre Consult Update'
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].body
            expected = '6 overdue referrals'
            self.assertEqual(actual, expected)


class MultipleLawyersBulkEmailTestCase(TestCase):
    """
        Test Case:
            professional: multiple lawyers
            event_type: different workflow states
            email template: subject, body content 
    """

    def setUp(self):
        celeryapp.conf.update(CELERY_TASK_ALWAYS_EAGER=True)
        celeryapp.conf.update(CELERY_TASK_STORE_EAGER_RESULT=True)

        self.referral_source = ReferralSource.objects.create(source='DC Affordable Law Firm')

        self._update_template_subject('waiting_for_first_pre_consult_update',
                                      ContentType.objects.get_for_model(ReferralLawyerWorkflowState),
                                      'Waiting For First Pre Consult Update',
                                      '{{OVERDUE_MATTERS_LIST|length}} overdue referrals')
        self._update_template_subject('waiting_for_pre_consult_update',
                                      ContentType.objects.get_for_model(ReferralLawyerWorkflowState),
                                      'Waiting For Pre Consult Update',
                                      '{{OVERDUE_MATTERS_LIST|length}} overdue referrals')

    def _update_template_subject(self, workflow_state, content_type, subject, body=''):
        """ set a custom email template subject """

        event = EmailEventInactiveFor.objects.filter(workflow_state=workflow_state, template__workflow_type=content_type).first()
        event.template.subject = subject # custom subject for testing
        event.template.body = body # custom subject for testing
        event.template.save()

    def _update_workflows_status(self, next_node, workflows=[]):
        for workflow in workflows:
            _next_node = workflow.get_node(next_node)
            workflow.task_set.all().latest().finish()
            workflow.task_set.all().latest().start_next_tasks([_next_node])
            workflow.save()

    def _create_professionals(self, count=1):
        return [User.objects.create(email=f'a{i+1}@dcerefer.org', password='password') for i in range(count)]

    def _create_multiple_referrals_and_workflows(self, professional, count=1):
        referrals = []
        workflows = []
        for i in range(count):
            referral = Referral.objects.create(professional=professional, email=f'test{i+1}@example.com', referred_by=self.referral_source)
            workflow = ReferralLawyerWorkflowState.referral_received(referral=referral)
            referrals.append(referral)
            workflows.append(workflow) 

        mail.outbox = [] # clean initial email

        return referrals, workflows

    def tearDown(self):
        mail.outbox = [] # clean initial email

    def test__multiple_lawyers__each_receives_their_own_bulk_email__WHEN_multiple_lawyers_have_overdue_referrals(self):
        """ multiple professionals with multiple referrals on same state, receive just 1 bulk email each """

        # multiple professionals, multiple referrals created
        [self._create_multiple_referrals_and_workflows(professional, 5) for professional in self._create_professionals(5)]

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=9)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 5
            self.assertEqual(actual, expected)

            for msg in mail.outbox:
                self.assertEqual(msg.body, "5 overdue referrals")

    def test__multiple_lawyers__each_receives_ONLY_one_email_per_event_WHEN_lawyers_have_overdue_referrals_ACROSS_different_events(self):
        """ multiple professionals with multiple referrals on 3 different states, receive just 1 bulk email for each event """

        for professional in self._create_professionals(5):
            _, workflows = self._create_multiple_referrals_and_workflows(professional, 6)
            # update status of few referrals
            self._update_workflows_status('waiting_for_pre_consult_update', workflows[2:4])
            self._update_workflows_status('waiting_for_post_consult_update', workflows[4:6])

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=30)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 15 # 5 professionals, has overdue across 3 different events
            self.assertEqual(actual, expected)

    def test__multiple_lawyers__emails_sent_only_to_lawyers_with_overdue_referrals__WHEN_some_lawyers_have_no_overdue_referrals(self):
        """ multiple professionals but only few has overdue referrals on a state, so only those professionals receive bulk email """

        for professional in self._create_professionals(5):
            _, workflows = self._create_multiple_referrals_and_workflows(professional, 6)
            self._update_workflows_status('waiting_for_pre_consult_update', workflows)

        # day 20th, few lawyers update their referrals
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=20)):
            for workflow in ReferralLawyerWorkflowState.objects.filter(referral__professional__in=User.objects.order_by('?')[:2]):
                workflow.hours_worked = 1
                workflow.save()

        # day 30th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=30)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 3
            self.assertEqual(actual, expected)


class MediatorInactiveAtFirstPreConsultTestCase(TestCase):
    """
        Test Case:
            professional: mediator
            event_type: 'waiting_for_first_pre_consult_update'
            days_inactive: 9
    """

    def setUp(self):
        celeryapp.conf.update(CELERY_TASK_ALWAYS_EAGER=True)
        celeryapp.conf.update(CELERY_TASK_STORE_EAGER_RESULT=True)

        self.professional = User.objects.create(email='a1@dcerefer.org', password='password')
        self.referral_source = ReferralSource.objects.create(source='DC Affordable Law Firm')

        self.email_subject = 'Waiting For First Pre Consult Update'
        self._update_template_subject('waiting_for_first_pre_consult_update', ContentType.objects.get_for_model(ReferralMediatorWorkflowState), self.email_subject)

    def _update_template_subject(self, workflow_state, content_type, subject):
        """ set a custom email template subject"""

        event = EmailEventInactiveFor.objects.filter(workflow_state=workflow_state,
                                                     template__workflow_type=content_type).first()
        event.template.subject = subject # custom subject for testing
        event.template.save()

    def _create_referral_and_workflow(self):

        referral = Referral.objects.create(professional=self.professional, email='test1@client.com', referred_by=self.referral_source)
        workflow = ReferralMediatorWorkflowState.referral_received(referral=referral)
        mail.outbox = [] # clean initial email

        return referral, workflow

    def tearDown(self):
        mail.outbox = [] # clean initial email

    def test__NO_email_sent__BEFORE_9th_day__WHEN_workflow_state_IS_waiting_for_first_pre_consult_update(self):
        """ no email sent, if 9 days not passed """

        referral, workflow = self._create_referral_and_workflow()

        # day 8th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=8)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 0
            self.assertEqual(actual, expected)

    def test__send_email_to_professional__ON_9th_day__WHEN_workflow_state_IS_waiting_for_first_pre_consult_update(self):
        """ email sent, on 9th day """

        referral, workflow = self._create_referral_and_workflow()

        # day 9th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=9)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].to[0]
            expected = self.professional.email
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = self.email_subject
            self.assertEqual(actual, expected)
    
    def test__send_email_to_professional__AFTER_9th_day__WHEN_workflow_state_IS_waiting_for_first_pre_consult_update(self):
        """ email sent, even if task ran after 9th day i.e. say on 15th day """

        referral, workflow = self._create_referral_and_workflow()

        # day 15th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=15)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].to[0]
            expected = self.professional.email
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = self.email_subject
            self.assertEqual(actual, expected)

    def test__NO_email_sent__WHEN_mediator_provides_human_update__BEFORE_9th_day__AT_waiting_for_first_pre_consult_update(self):
        """ email not sent on 9th day, if mediator updated status on 6th day """
        
        referral, workflow = self._create_referral_and_workflow()

        # day 6th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=6)):
            workflow.hours_worked = 1
            workflow.save()

        # day 9th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=9)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 0
            self.assertEqual(actual, expected)

    def test__email_sent_again__WHEN_9_days_pass_AFTER_human_update__AT_waiting_for_first_pre_consult_update(self):
        """ email sent on 15th day, if mediator updated status on 6th day i.e. 9 days after 6th day update """

        referral, workflow = self._create_referral_and_workflow()

        # day 6th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=6)):
            workflow.hours_worked = 1
            workflow.save()

        # day 15th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=15)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].to[0]
            expected = self.professional.email
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = self.email_subject
            self.assertEqual(actual, expected)


class MediatorInactiveAtPreConsultBothPartyTestCase(TestCase):
    """
        Test Case:
            professional: mediator
            event_type: 'waiting_for_pre_consult_update_from_both_party'
            days_inactive: 30
    """

    def setUp(self):
        celeryapp.conf.update(CELERY_TASK_ALWAYS_EAGER=True)
        celeryapp.conf.update(CELERY_TASK_STORE_EAGER_RESULT=True)

        self.professional = User.objects.create(email='a1@dcerefer.org', password='password')
        self.referral_source = ReferralSource.objects.create(source='DC Affordable Law Firm')

        self.email_subject = 'Waiting For Pre Consult Update'
        self._update_template_subject('waiting_for_pre_consult_update_from_both_party', ContentType.objects.get_for_model(ReferralMediatorWorkflowState), self.email_subject)

    def _update_template_subject(self, workflow_state, content_type, subject):
        """ set a custom email template subject"""

        event = EmailEventInactiveFor.objects.filter(workflow_state=workflow_state,
                                                     template__workflow_type=content_type).first()
        event.template.subject = subject # custom subject for testing
        event.template.save()

    def _create_referral_and_workflow(self):

        referral = Referral.objects.create(professional=self.professional, email='test1@client.com', referred_by=self.referral_source)
        workflow = ReferralMediatorWorkflowState.referral_received(referral=referral)
        mail.outbox = [] # clean initial email

        _next_node = workflow.get_node('waiting_for_pre_consult_update_from_both_party')
        workflow.task_set.all().latest().finish()
        workflow.task_set.all().latest().start_next_tasks([_next_node])
        workflow.save()

        return referral, workflow

    def tearDown(self):
        mail.outbox = [] # clean initial email

    def test__NO_email_sent__BEFORE_30th_day__WHEN_workflow_state_IS_waiting_for_pre_consult_update_from_both_party(self):
        """ no email sent, if 30 days not passed """

        referral, workflow = self._create_referral_and_workflow()

        # day 28th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=28)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 0
            self.assertEqual(actual, expected)

    def test__send_email_to_professional__ON_30th_day__WHEN_workflow_state_IS_waiting_for_pre_consult_update_from_both_party(self):
        """ email sent, on 30th day """

        referral, workflow = self._create_referral_and_workflow()

        # day 30th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=30)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].to[0]
            expected = self.professional.email
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = self.email_subject
            self.assertEqual(actual, expected)
    
    def test__send_email_to_professional__AFTER_30th_day__WHEN_workflow_state_IS_waiting_for_pre_consult_update_from_both_party(self):
        """ email sent, even if task ran after 30th day i.e. say on 40th day """

        referral, workflow = self._create_referral_and_workflow()

        # day 40th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=40)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].to[0]
            expected = self.professional.email
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = self.email_subject
            self.assertEqual(actual, expected)
    
    def test__NO_email_sent__WHEN_mediator_provides_human_update__BEFORE_30th_day__AT_waiting_for_pre_consult_update_from_both_party(self):
        """ email not sent on 30th day, if mediator updated status on 10th day """

        referral, workflow = self._create_referral_and_workflow()

        # day 10th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=10)):
            workflow.hours_worked = 1
            workflow.save()

        # day 30th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=30)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 0
            self.assertEqual(actual, expected)

    def test__email_sent_again__WHEN_30_days_pass_AFTER_human_update__AT_waiting_for_pre_consult_update_from_both_party(self):
        """ email sent on 40th day, if mediator updated status on 10th day i.e. 30 days after 10th day update"""

        referral, workflow = self._create_referral_and_workflow()

        # day 10th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=10)):
            workflow.hours_worked = 1
            workflow.save()

        # day 40th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=40)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].to[0]
            expected = self.professional.email
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = self.email_subject
            self.assertEqual(actual, expected)



class MediatorInactiveAtPreConsultOtherPartyTestCase(TestCase):
    """
        Test Case:
            professional: mediator
            event_type: 'waiting_for_pre_consult_update_from_other_party'
            days_inactive: 30
    """

    def setUp(self):
        celeryapp.conf.update(CELERY_TASK_ALWAYS_EAGER=True)
        celeryapp.conf.update(CELERY_TASK_STORE_EAGER_RESULT=True)

        self.professional = User.objects.create(email='a1@dcerefer.org', password='password')
        self.referral_source = ReferralSource.objects.create(source='DC Affordable Law Firm')

        self.email_subject = 'Waiting For Pre Consult Update'
        self._update_template_subject('waiting_for_pre_consult_update_from_other_party', ContentType.objects.get_for_model(ReferralMediatorWorkflowState), self.email_subject)

    def _update_template_subject(self, workflow_state, content_type, subject):
        """ set a custom email template subject"""

        event = EmailEventInactiveFor.objects.filter(workflow_state=workflow_state,
                                                     template__workflow_type=content_type).first()
        event.template.subject = subject # custom subject for testing
        event.template.save()

    def _create_referral_and_workflow(self):

        referral = Referral.objects.create(professional=self.professional, email='test1@client.com', referred_by=self.referral_source)
        workflow = ReferralMediatorWorkflowState.referral_received(referral=referral)
        mail.outbox = [] # clean initial email

        _next_node = workflow.get_node('waiting_for_pre_consult_update_from_other_party')
        workflow.task_set.all().latest().finish()
        workflow.task_set.all().latest().start_next_tasks([_next_node])
        workflow.save()

        return referral, workflow

    def tearDown(self):
        mail.outbox = [] # clean initial email

    def test__NO_email_sent__BEFORE_30th_day__WHEN_workflow_state_IS_waiting_for_pre_consult_update_from_other_party(self):
        """ no email sent, if 30 days not passed """

        referral, workflow = self._create_referral_and_workflow()

        # day 28th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=28)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 0
            self.assertEqual(actual, expected)

    def test__send_email_to_professional__ON_30th_day__WHEN_workflow_state_IS_waiting_for_pre_consult_update_from_other_party(self):
        """ email sent, on 30th day """

        referral, workflow = self._create_referral_and_workflow()

        # day 30th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=30)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].to[0]
            expected = self.professional.email
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = self.email_subject
            self.assertEqual(actual, expected)
    
    def test__send_email_to_professional__AFTER_30th_day__WHEN_workflow_state_IS_waiting_for_pre_consult_update_from_other_party(self):
        """ email sent, even if task ran after 30th day i.e. say on 40th day """

        referral, workflow = self._create_referral_and_workflow()

        # day 40th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=40)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].to[0]
            expected = self.professional.email
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = self.email_subject
            self.assertEqual(actual, expected)
    
    def test__NO_email_sent__WHEN_mediator_provides_human_update__BEFORE_30th_day__AT_waiting_for_pre_consult_update_from_other_party(self):
        """ email not sent on 30th day, if mediator updated status on 10th day """

        referral, workflow = self._create_referral_and_workflow()

        # day 10th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=10)):
            workflow.hours_worked = 1
            workflow.save()

        # day 30th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=30)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 0
            self.assertEqual(actual, expected)

    def test__email_sent_again__WHEN_30_days_pass_AFTER_human_update__AT_waiting_for_pre_consult_update_from_other_party(self):
        """ email sent on 40th day, if mediator updated status on 10th day i.e. 30 days after 10th day update"""

        referral, workflow = self._create_referral_and_workflow()

        # day 10th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=10)):
            workflow.hours_worked = 1
            workflow.save()

        # day 40th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=40)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].to[0]
            expected = self.professional.email
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = self.email_subject
            self.assertEqual(actual, expected)


class MediatorInactiveAtPostConsultTestCase(TestCase):
    """
        Test Case:
            professional: mediator
            event_type: 'waiting_for_post_consult_update'
            days_inactive: 30
    """

    def setUp(self):
        celeryapp.conf.update(CELERY_TASK_ALWAYS_EAGER=True)
        celeryapp.conf.update(CELERY_TASK_STORE_EAGER_RESULT=True)

        self.professional = User.objects.create(email='a1@dcerefer.org', password='password')
        self.referral_source = ReferralSource.objects.create(source='DC Affordable Law Firm')

        self.email_subject = 'Waiting For Post Consult Update'
        self._update_template_subject('waiting_for_post_consult_update', ContentType.objects.get_for_model(ReferralMediatorWorkflowState), self.email_subject)

    def _update_template_subject(self, workflow_state, content_type, subject):
        """ set a custom email template subject"""

        event = EmailEventInactiveFor.objects.filter(workflow_state=workflow_state,
                                                     template__workflow_type=content_type).first()
        event.template.subject = subject # custom subject for testing
        event.template.save()

    def _create_referral_and_workflow(self):

        referral = Referral.objects.create(professional=self.professional, email='test1@client.com', referred_by=self.referral_source)
        workflow = ReferralMediatorWorkflowState.referral_received(referral=referral)
        mail.outbox = [] # clean initial email

        _next_node = workflow.get_node('waiting_for_post_consult_update')
        workflow.task_set.all().latest().finish()
        workflow.task_set.all().latest().start_next_tasks([_next_node])
        workflow.save()

        return referral, workflow

    def tearDown(self):
        mail.outbox = [] # clean initial email

    def test__NO_email_sent__BEFORE_30th_day__WHEN_workflow_state_IS_waiting_for_post_consult_update(self):
        """ no email sent, if 30 days not passed """

        referral, workflow = self._create_referral_and_workflow()

        # day 28th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=28)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 0
            self.assertEqual(actual, expected)

    def test__send_email_to_professional__ON_30th_day__WHEN_workflow_state_IS_waiting_for_post_consult_update(self):
        """ email sent, on 30th day """

        referral, workflow = self._create_referral_and_workflow()

        # day 30th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=30)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].to[0]
            expected = self.professional.email
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = self.email_subject
            self.assertEqual(actual, expected)
    
    def test__send_email_to_professional__AFTER_30th_day__WHEN_workflow_state_IS_waiting_for_post_consult_update(self):
        """ email sent, even if task ran after 30th day i.e. say on 40th day """

        referral, workflow = self._create_referral_and_workflow()

        # day 40th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=40)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].to[0]
            expected = self.professional.email
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = self.email_subject
            self.assertEqual(actual, expected)

    def test__NO_email_sent__WHEN_mediator_provides_human_update__BEFORE_30th_day__AT_waiting_for_post_consult_update(self):
        """ email not sent on 30th day, if mediator updated status on 10th day """
        
        referral, workflow = self._create_referral_and_workflow()

        # day 10th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=10)):
            workflow.hours_worked = 1
            workflow.save()

        # day 30th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=30)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 0
            self.assertEqual(actual, expected)

    def test__email_sent_again__WHEN_30_days_pass_AFTER_human_update__AT_waiting_for_post_consult_update(self):
        """ email sent on 40th day, if mediator updated status on 10th day i.e. 30 days after 10th day update"""

        referral, workflow = self._create_referral_and_workflow()

        # day 10th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=10)):
            workflow.hours_worked = 1
            workflow.save()

        # day 40th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=40)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].to[0]
            expected = self.professional.email
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = self.email_subject
            self.assertEqual(actual, expected)


class MediatorInactiveAtPostEngagementTestCase(TestCase):
    """
        Test Case:
            professional: mediator
            event_type: 'waiting_for_post_engagement_update'
            days_inactive: 90
    """

    def setUp(self):
        celeryapp.conf.update(CELERY_TASK_ALWAYS_EAGER=True)
        celeryapp.conf.update(CELERY_TASK_STORE_EAGER_RESULT=True)

        self.professional = User.objects.create(email='a1@dcerefer.org', password='password')
        self.referral_source = ReferralSource.objects.create(source='DC Affordable Law Firm')

        self.email_subject = 'Waiting For Post Engagement Update'
        self._update_template_subject('waiting_for_post_engagement_update', ContentType.objects.get_for_model(ReferralMediatorWorkflowState), self.email_subject)

    def _update_template_subject(self, workflow_state, content_type, subject):
        """ set a custom email template subject"""

        event = EmailEventInactiveFor.objects.filter(workflow_state=workflow_state,
                                                     template__workflow_type=content_type).first()
        event.template.subject = subject # custom subject for testing
        event.template.save()

    def _create_referral_and_workflow(self):

        referral = Referral.objects.create(professional=self.professional, email='test1@client.com', referred_by=self.referral_source)
        workflow = ReferralMediatorWorkflowState.referral_received(referral=referral)
        mail.outbox = [] # clean initial email

        _next_node = workflow.get_node('waiting_for_post_engagement_update')
        workflow.task_set.all().latest().finish()
        workflow.task_set.all().latest().start_next_tasks([_next_node])
        workflow.save()

        return referral, workflow

    def tearDown(self):
        mail.outbox = [] # clean initial email

    def test__NO_email_sent__BEFORE_90th_day__WHEN_workflow_state_IS_waiting_for_post_engagement_update(self):
        """ no email sent, if 90 days not passed """

        referral, workflow = self._create_referral_and_workflow()

        # day 58th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=58)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 0
            self.assertEqual(actual, expected)

    def test__send_email_to_professional__ON_90th_day__WHEN_workflow_state_IS_waiting_for_post_engagement_update(self):
        """ email sent, on 90th day """

        referral, workflow = self._create_referral_and_workflow()

        # day 90th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=90)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].to[0]
            expected = self.professional.email
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = self.email_subject
            self.assertEqual(actual, expected)
    
    def test__send_email_to_professional__AFTER_90th_day__WHEN_workflow_state_IS_waiting_for_post_engagement_update(self):
        """ email sent, even if task ran after 90th day i.e. say on 110th day """

        referral, workflow = self._create_referral_and_workflow()

        # day 110th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=110)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].to[0]
            expected = self.professional.email
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = self.email_subject
            self.assertEqual(actual, expected)
    
    def test__NO_email_sent__WHEN_mediator_provides_human_update__BEFORE_90th_day__AT_waiting_for_post_engagement_update(self):
        """ email not sent on 90th day, if mediator updated status on 50th day """
        
        referral, workflow = self._create_referral_and_workflow()

        # day 50th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=50)):
            workflow.hours_worked = 1
            workflow.save()

        # day 90th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=90)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 0
            self.assertEqual(actual, expected)

    def test__email_sent_again__WHEN_90_days_pass_AFTER_human_update__AT_waiting_for_post_engagement_update(self):
        """ email sent on 140th day, if mediator updated status on 50th day i.e. 90 days after 50th day update"""

        referral, workflow = self._create_referral_and_workflow()

        # day 50th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=50)):
            workflow.hours_worked = 1
            workflow.save()

        # day 140th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=140)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].to[0]
            expected = self.professional.email
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = self.email_subject
            self.assertEqual(actual, expected)


class SingleMediatorBulkEmailTestCase(TestCase):
    """
        Test Case:
            professional: single mediator
            event_type: different workflow states
            email template: subject, body content 
    """

    def setUp(self):
        celeryapp.conf.update(CELERY_TASK_ALWAYS_EAGER=True)
        celeryapp.conf.update(CELERY_TASK_STORE_EAGER_RESULT=True)

        self.professional = User.objects.create(email='a1@dcerefer.org', password='password')
        self.referral_source = ReferralSource.objects.create(source='DC Affordable Law Firm')

        self._update_template_subject('waiting_for_first_pre_consult_update',
                                      ContentType.objects.get_for_model(ReferralMediatorWorkflowState),
                                      'Waiting For First Pre Consult Update',
                                      '{{OVERDUE_MATTERS_LIST|length}} overdue referrals')
        self._update_template_subject('waiting_for_pre_consult_update_from_both_party',
                                      ContentType.objects.get_for_model(ReferralMediatorWorkflowState),
                                      'Waiting For Pre Consult Update',
                                      '{{OVERDUE_MATTERS_LIST|length}} overdue referrals')

    def _update_template_subject(self, workflow_state, content_type, subject, body=''):
        """ set a custom email template subject"""

        event = EmailEventInactiveFor.objects.filter(workflow_state=workflow_state,
                                                     template__workflow_type=content_type).first()
        event.template.subject = subject # custom subject for testing
        event.template.body = body # custom subject for testing
        event.template.save()

    def _update_workflows_status(self, next_node, workflows=[]):
        for workflow in workflows:
            _next_node = workflow.get_node(next_node)
            workflow.task_set.all().latest().finish()
            workflow.task_set.all().latest().start_next_tasks([_next_node])
            workflow.save()

    def _create_multiple_referrals_and_workflows(self, count=1):
        referrals = []
        workflows = []
        for i in range(count):
            referral = Referral.objects.create(professional=self.professional, email=f'test{i+1}@example.com', referred_by=self.referral_source)
            workflow = ReferralMediatorWorkflowState.referral_received(referral=referral)
            referrals.append(referral)
            workflows.append(workflow) 

        mail.outbox = [] # clean initial email

        return referrals, workflows

    def tearDown(self):
        mail.outbox = [] # clean initial email

    def test__send_single_email_WITH_multiple_referrals_WHEN_multiple_referrals_overdue_FOR_same_professional__FOR_same_event_type(self):
        """ Multiple referrals for mediator, however only 1 overdue email sent """

        _, workflows = self._create_multiple_referrals_and_workflows(10)

        # day 9th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=9)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = 'Waiting For First Pre Consult Update'
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].body
            expected = '10 overdue referrals'
            self.assertEqual(actual, expected)

    def test__send_separate_emails_WHEN_referrals_overdue_at_different_states_FOR_same_professional(self):
        """ Multiple referrals overdue at different states, however, for each state only 1 email sent """

        _, workflows = self._create_multiple_referrals_and_workflows(10)

        # update few referrals to 'waiting_for_pre_consult_update_from_both_party'
        self._update_workflows_status('waiting_for_pre_consult_update_from_both_party', random.sample(workflows, 4))

        # day 30th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=30)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 2
            self.assertEqual(actual, expected)

            # email 1
            actual = mail.outbox[0].subject
            expected = 'Waiting For First Pre Consult Update'
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].body
            expected = '6 overdue referrals'
            self.assertEqual(actual, expected)

            # email 2
            actual = mail.outbox[1].subject
            expected = 'Waiting For Pre Consult Update'
            self.assertEqual(actual, expected)

            actual = mail.outbox[1].body
            expected = '4 overdue referrals'
            self.assertEqual(actual, expected)

    def test__bulk_email_contains_only_overdue_referrals__WHEN_same_mediator_has_overdue_and_non_overdue_referrals(self):
        """ in email, list only overdue emails, not the one recently updated """

        _, workflows = self._create_multiple_referrals_and_workflows(10)

        # update all referrals to 'waiting_for_pre_consult_update_from_both_party' at once, to use 30 days overdue schedule
        self._update_workflows_status('waiting_for_pre_consult_update_from_both_party', workflows)

        # day 20th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=20)):
            # update 4 random workflows
            self._update_workflows_status('waiting_for_pre_consult_update_from_both_party', random.sample(workflows, 4))

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=30)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 1
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].subject
            expected = 'Waiting For Pre Consult Update'
            self.assertEqual(actual, expected)

            actual = mail.outbox[0].body
            expected = '6 overdue referrals'
            self.assertEqual(actual, expected)


class MultipleMediatorsBulkEmailTestCase(TestCase):
    """
        Test Case:
            professional: multiple mediators
            event_type: different workflow states
            email template: subject, body content 
    """

    def setUp(self):
        celeryapp.conf.update(CELERY_TASK_ALWAYS_EAGER=True)
        celeryapp.conf.update(CELERY_TASK_STORE_EAGER_RESULT=True)

        self.referral_source = ReferralSource.objects.create(source='DC Affordable Law Firm')

        self._update_template_subject('waiting_for_first_pre_consult_update',
                                      ContentType.objects.get_for_model(ReferralMediatorWorkflowState),
                                      'Waiting For First Pre Consult Update',
                                      '{{OVERDUE_MATTERS_LIST|length}} overdue referrals')
        self._update_template_subject('waiting_for_pre_consult_update_from_both_party',
                                      ContentType.objects.get_for_model(ReferralMediatorWorkflowState),
                                      'Waiting For Pre Consult Update',
                                      '{{OVERDUE_MATTERS_LIST|length}} overdue referrals')

    def _update_template_subject(self, workflow_state, content_type, subject, body=''):
        """ set a custom email template subject """

        event = EmailEventInactiveFor.objects.filter(workflow_state=workflow_state, template__workflow_type=content_type).first()
        event.template.subject = subject # custom subject for testing
        event.template.body = body # custom subject for testing
        event.template.save()

    def _update_workflows_status(self, next_node, workflows=[]):
        for workflow in workflows:
            _next_node = workflow.get_node(next_node)
            workflow.task_set.all().latest().finish()
            workflow.task_set.all().latest().start_next_tasks([_next_node])
            workflow.save()

    def _create_professionals(self, count=1):
        return [User.objects.create(email=f'a{i+1}@dcerefer.org', password='password') for i in range(count)]

    def _create_multiple_referrals_and_workflows(self, professional, count=1):
        referrals = []
        workflows = []
        for i in range(count):
            referral = Referral.objects.create(professional=professional, email=f'test{i+1}@example.com', referred_by=self.referral_source)
            workflow = ReferralMediatorWorkflowState.referral_received(referral=referral)
            referrals.append(referral)
            workflows.append(workflow) 

        mail.outbox = [] # clean initial email

        return referrals, workflows

    def tearDown(self):
        mail.outbox = [] # clean initial email

    def test__multiple_mediators__each_receives_their_own_bulk_email__WHEN_multiple_mediators_have_overdue_referrals(self):
        """ multiple professionals with multiple referrals on same state, receive just 1 bulk email each """

        # multiple professionals, multiple referrals created
        [self._create_multiple_referrals_and_workflows(professional, 5) for professional in self._create_professionals(5)]

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=9)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 5
            self.assertEqual(actual, expected)

            for msg in mail.outbox:
                self.assertEqual(msg.body, "5 overdue referrals")

    def test__multiple_mediators__each_receives_ONLY_one_email_per_event_WHEN_mediators_have_overdue_referrals_ACROSS_different_events(self):
        """ multiple professionals with multiple referrals on 3 different states, receive just 1 bulk email for each event """

        for professional in self._create_professionals(5):
            _, workflows = self._create_multiple_referrals_and_workflows(professional, 6)
            # update status of few referrals
            self._update_workflows_status('waiting_for_pre_consult_update_from_both_party', workflows[2:4])
            self._update_workflows_status('waiting_for_post_consult_update', workflows[4:6])

        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=30)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 15 # 5 professionals, has overdue across 3 different events
            self.assertEqual(actual, expected)

    def test__multiple_mediators__emails_sent_only_to_mediators_with_overdue_referrals__WHEN_some_mediators_have_no_overdue_referrals(self):
        """ multiple professionals but only few has overdue referrals on a state, so only those professionals receive bulk email """

        for professional in self._create_professionals(5):
            _, workflows = self._create_multiple_referrals_and_workflows(professional, 6)
            self._update_workflows_status('waiting_for_pre_consult_update_from_both_party', workflows)

        # day 20th, few mediators update their referrals
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=20)):
            for workflow in ReferralMediatorWorkflowState.objects.filter(referral__professional__in=User.objects.order_by('?')[:2]):
                workflow.hours_worked = 1
                workflow.save()

        # day 30th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=30)):
            send_scheduled_notification_emails() # run task

            actual = len(mail.outbox)
            expected = 3
            self.assertEqual(actual, expected)
