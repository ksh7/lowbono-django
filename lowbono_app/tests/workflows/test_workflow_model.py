import datetime
import random
from django.core import mail
from django.apps import apps
from django.utils import timezone
from django.test import TestCase
from django.contrib.contenttypes.models import ContentType

from unittest.mock import patch

from lowbono.celery import app as celeryapp
from lowbono_app.models import User, Referral, ReferralSource, EmailEventInactiveFor
from lowbono_lawyer.workflows import ReferralLawyerWorkflowState
import inspect


class GetOverdueProfessionalsMethodTestCase(TestCase):
    """
        Test Case for User Manager's 'overdue_professionals_for_event' method
    """

    def setUp(self):
        celeryapp.conf.update(CELERY_TASK_ALWAYS_EAGER=True)
        celeryapp.conf.update(CELERY_TASK_STORE_EAGER_RESULT=True)
        self.referral_source = ReferralSource.objects.create(source='DC Affordable Law Firm')

    def _update_workflows_status(self, next_node, workflows=[]):
        for workflow in workflows:
            _next_node = workflow.get_node(next_node)
            workflow.task_set.all().latest().finish()
            workflow.task_set.all().latest().start_next_tasks([_next_node])
            workflow.save()

    def _create_professionals(self, count=1):
        return [User.objects.create(email=f'a{i+1}@example.org', password='password') for i in range(count)]

    def _create_multiple_referrals_and_workflows(self, professional, count=1):
        referrals = []
        workflows = []
        for i in range(count):
            referral = Referral.objects.create(professional=professional, email=f'test{i+1}@example.com', referred_by=self.referral_source)
            workflow = ReferralLawyerWorkflowState.referral_received(referral=referral)
            referrals.append(referral)
            workflows.append(workflow)

        mail.outbox = []  # clean initial email
        return referrals, workflows
    
    def _get_event_type(self, workflow_state):
        return EmailEventInactiveFor.objects.get(workflow_state=workflow_state, template__workflow_type=ContentType.objects.get_for_model(ReferralLawyerWorkflowState))

    def tearDown(self):
        mail.outbox = []

    def test__overdue_professionals_for_event__returns_empty_list_WHEN_workflows_exist_BUT_not_overdue(self):

        professionals = self._create_professionals(count=1)
        professional = professionals[0]
        referrals, workflows = self._create_multiple_referrals_and_workflows(professional, count=1)
        event_type = self._get_event_type('waiting_for_first_pre_consult_update')

        # Day 8th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=8)):
            overdue_professional_ids = User.objects.overdue_professionals_for_event(event_type).values_list('id', flat=True)
            self.assertEqual(list(overdue_professional_ids), [])
            self.assertEqual(len(overdue_professional_ids), 0)

    def test__overdue_professionals_for_event__returns_professional_WHEN_workflow_is_overdue(self):

        professionals = self._create_professionals(count=1)
        professional = professionals[0]
        referrals, workflows = self._create_multiple_referrals_and_workflows(professionals[0], count=1)
        event_type = self._get_event_type('waiting_for_first_pre_consult_update') # 9 days event

        # Day 9th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=9)):
            overdue_professional_ids = User.objects.overdue_professionals_for_event(event_type).values_list('id', flat=True)
            self.assertEqual(list(overdue_professional_ids), [professional.id])
            self.assertEqual(len(overdue_professional_ids), 1)

    def test__overdue_professionals_for_event__returns_single_professional_WHEN_same_professional_has_multiple_overdue_workflows(self):

        professionals = self._create_professionals(count=1)
        professional = professionals[0]
        referrals, workflows = self._create_multiple_referrals_and_workflows(professional, count=5)
        event_type = self._get_event_type('waiting_for_first_pre_consult_update') # 9 days event

        # Day 9th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=9)):
            overdue_professional_ids = User.objects.overdue_professionals_for_event(event_type).values_list('id', flat=True)

            # Only one professional ID returned despite 3 overdue workflows
            self.assertEqual(list(overdue_professional_ids), [professional.id])
            self.assertEqual(len(overdue_professional_ids), 1)
    
    def test__overdue_professionals_for_event__returns_multiple_professionals_WHEN_multiple_professionals_have_overdue_workflows(self):

        professionals = self._create_professionals(count=2)
        lawyer1 = professionals[0]
        lawyer2 = professionals[1]
        referrals1, workflows1 = self._create_multiple_referrals_and_workflows(lawyer1, count=2)
        referrals2, workflows2 = self._create_multiple_referrals_and_workflows(lawyer2, count=1)
        event_type = self._get_event_type('waiting_for_first_pre_consult_update') # 9 days event

        # Day 9th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=9)):
            overdue_professional_ids = User.objects.overdue_professionals_for_event(event_type).values_list('id', flat=True)
            overdue_ids_list = list(overdue_professional_ids)
            self.assertEqual(len(overdue_ids_list), 2)
            self.assertIn(lawyer1.id, overdue_ids_list)
            self.assertIn(lawyer2.id, overdue_ids_list)

    def test__overdue_professionals_for_event__returns_professionals_only_for_specified_workflow_state(self):

        professionals = self._create_professionals(count=2)
        lawyer1 = professionals[0]
        lawyer2 = professionals[1]
        referrals1, workflows1 = self._create_multiple_referrals_and_workflows(lawyer1, count=1)
        referrals2, workflows2 = self._create_multiple_referrals_and_workflows(lawyer2, count=1)
        # lawyer2's workflow to a different state
        self._update_workflows_status('waiting_for_post_consult_update', workflows2) # 30 days event

        event_type_first = self._get_event_type('waiting_for_first_pre_consult_update') # 9 days event

        # Day 30th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=30)):
            overdue_professional_ids = User.objects.overdue_professionals_for_event(event_type_first).values_list('id', flat=True)

            # Only lawyer1 returned, as lawyer2 is in different state
            overdue_ids_list = list(overdue_professional_ids)
            self.assertEqual(len(overdue_ids_list), 1)
            self.assertEqual(overdue_ids_list[0], lawyer1.id)
            self.assertNotIn(lawyer2.id, overdue_ids_list)
    
    def test__overdue_professionals_for_event__returns_empty_WHEN_human_update_exists_within_schedule(self):

        professionals = self._create_professionals(count=1)
        professional = professionals[0]
        referrals, workflows = self._create_multiple_referrals_and_workflows(professional, count=1)
        workflow = workflows[0]
        event_type = self._get_event_type('waiting_for_first_pre_consult_update') # 9 days event

        # Day 5th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=5)):
            workflow.is_human_activity = True
            workflow.hours_worked = 2.5
            workflow.save()

        # Day 10th, only 5 from last human update
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=10)):
            overdue_professional_ids = User.objects.overdue_professionals_for_event(event_type).values_list('id', flat=True)

            # No overdue professionals, as human update was within schedule
            self.assertEqual(list(overdue_professional_ids), [])
            self.assertEqual(len(overdue_professional_ids), 0)

    def test__overdue_professionals_for_event__returns_professional_WHEN_last_human_update_exceeds_schedule(self):

        professionals = self._create_professionals(count=1)
        professional = professionals[0]
        referrals, workflows = self._create_multiple_referrals_and_workflows(professional, count=1)
        workflow = workflows[0]
        self._update_workflows_status('waiting_for_pre_consult_update', workflows)  # update to 30 days event
        event_type = self._get_event_type('waiting_for_pre_consult_update') # 9 days event

        # Day 10th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=10)):
            workflow.is_human_activity = True
            workflow.hours_worked = 1
            workflow.save()

        # Day 30th, 20 days from human update
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=30)):
            overdue_professional_ids = User.objects.overdue_professionals_for_event(event_type).values_list('id', flat=True)

            # Professional is not overdue, 40 days > 30 days schedule
            self.assertEqual(list(overdue_professional_ids), [])
            self.assertEqual(len(overdue_professional_ids), 0)

        # Day 40th, 30 days from human update
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=40)):
            overdue_professional_ids = User.objects.overdue_professionals_for_event(event_type).values_list('id', flat=True)

            # Professional is overdue
            self.assertEqual(list(overdue_professional_ids), [professional.id])
            self.assertEqual(len(overdue_professional_ids), 1)


class GetOverdueWorkflowsForProfessionalMethodTestCase(TestCase):
    """
        Test Case for ReferralWorkflowStateBaseManager's 'get_overdue_workflows_for_professional' method
    """

    def setUp(self):
        celeryapp.conf.update(CELERY_TASK_ALWAYS_EAGER=True)
        celeryapp.conf.update(CELERY_TASK_STORE_EAGER_RESULT=True)
        self.referral_source = ReferralSource.objects.create(source='DC Affordable Law Firm')
    
    def _update_workflows_status(self, next_node, workflows=[]):
        for workflow in workflows:
            _next_node = workflow.get_node(next_node)
            workflow.task_set.all().latest().finish()
            workflow.task_set.all().latest().start_next_tasks([_next_node])
            workflow.save()
    
    def _create_professionals(self, count=1):
        return [User.objects.create(email=f'a{i+1}@example.org', password='password') for i in range(count)]
    
    def _create_multiple_referrals_and_workflows(self, professional, count=1):
        referrals = []
        workflows = []
        for i in range(count):
            referral = Referral.objects.create(professional=professional, email=f'test{i+1}@example.com', referred_by=self.referral_source)
            workflow = ReferralLawyerWorkflowState.referral_received(referral=referral)
            referrals.append(referral)
            workflows.append(workflow)

        mail.outbox = []  # clean initial email
        return referrals, workflows
    
    def _get_event_type(self, workflow_state):
        return EmailEventInactiveFor.objects.get(workflow_state=workflow_state, template__workflow_type=ContentType.objects.get_for_model(ReferralLawyerWorkflowState))

    def tearDown(self):
        mail.outbox = []

    def test__get_overdue_workflows_for_professional__returns_empty_queryset_WHEN_no_workflows_for_professional(self):

        professionals = self._create_professionals(count=1)
        professional = professionals[0]
        event_type = self._get_event_type('waiting_for_first_pre_consult_update')

        # Day 10th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=10)):
            overdue_workflows = ReferralLawyerWorkflowState.objects.get_overdue_workflows_for_professional(event_type=event_type, professional=professional)
            self.assertEqual(overdue_workflows.count(), 0)
            self.assertFalse(overdue_workflows.exists())

    def test__get_overdue_workflows_for_professional__returns_empty_queryset_WHEN_workflows_not_overdue(self):

        professionals = self._create_professionals(count=1)
        professional = professionals[0]
        referrals, workflows = self._create_multiple_referrals_and_workflows(professional, count=5)
        event_type = self._get_event_type('waiting_for_first_pre_consult_update')

        # Day 8th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=8)):
            overdue_workflows = ReferralLawyerWorkflowState.objects.get_overdue_workflows_for_professional(event_type=event_type, professional=professional)
            self.assertEqual(overdue_workflows.count(), 0)

    def test__get_overdue_workflows_for_professional__returns_workflow_WHEN_overdue_at_specified_state(self):

        professionals = self._create_professionals(count=1)
        professional = professionals[0]
        referrals, workflows = self._create_multiple_referrals_and_workflows(professional, count=1)
        event_type = self._get_event_type('waiting_for_first_pre_consult_update')

        # Day 9th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=9)):
            overdue_workflows = ReferralLawyerWorkflowState.objects.get_overdue_workflows_for_professional(event_type=event_type, professional=professional)
            self.assertEqual(overdue_workflows.count(), 1)
            self.assertEqual(overdue_workflows.first().id, workflows[0].id)

    def test__get_overdue_workflows_for_professional__returns_multiple_workflows_WHEN_multiple_overdue(self):

        professionals = self._create_professionals(count=1)
        professional = professionals[0]
        referrals, workflows = self._create_multiple_referrals_and_workflows(professional, count=3)
        event_type = self._get_event_type('waiting_for_first_pre_consult_update')

        # Day 10th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=10)):
            overdue_workflows = ReferralLawyerWorkflowState.objects.get_overdue_workflows_for_professional(event_type=event_type, professional=professional)
            self.assertEqual(overdue_workflows.count(), 3)
            workflow_ids = [w.id for w in overdue_workflows]
            for workflow in workflows:
                self.assertIn(workflow.id, workflow_ids)

    def test__get_overdue_workflows_for_professional__returns_only_workflows_at_specified_state(self):

        professionals = self._create_professionals(count=1)
        professional = professionals[0]
        referrals, workflows = self._create_multiple_referrals_and_workflows(professional, count=3)

        # Move 1 workflow to different state
        self._update_workflows_status('waiting_for_pre_consult_update', [workflows[2]])

        event_type = self._get_event_type('waiting_for_first_pre_consult_update')

        # Day 10th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=10)):
            overdue_workflows = ReferralLawyerWorkflowState.objects.get_overdue_workflows_for_professional(event_type=event_type, professional=professional)
            self.assertEqual(overdue_workflows.count(), 2)
            workflow_ids = [w.id for w in overdue_workflows]
            self.assertIn(workflows[0].id, workflow_ids)
            self.assertIn(workflows[1].id, workflow_ids)
            self.assertNotIn(workflows[2].id, workflow_ids)

    def test__get_overdue_workflows_for_professional__returns_empty_WHEN_correct_professional_BUT_wrong_state(self):

        professionals = self._create_professionals(count=1)
        professional = professionals[0]
        referrals, workflows = self._create_multiple_referrals_and_workflows(professional, count=1)

        # Move workflow to different state
        self._update_workflows_status('waiting_for_pre_consult_update', workflows)

        event_type = self._get_event_type('waiting_for_first_pre_consult_update')

        # Day 35th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=35)):
            overdue_workflows = ReferralLawyerWorkflowState.objects.get_overdue_workflows_for_professional(event_type=event_type, professional=professional)
            self.assertEqual(overdue_workflows.count(), 0)

    def test__get_overdue_workflows_for_professional__returns_only_specified_professionals_workflows(self):

        professionals = self._create_professionals(count=2)
        lawyer1, lawyer2 = professionals[0], professionals[1]
        referrals1, workflows1 = self._create_multiple_referrals_and_workflows(lawyer1, count=2)
        referrals2, workflows2 = self._create_multiple_referrals_and_workflows(lawyer2, count=3)
        event_type = self._get_event_type('waiting_for_first_pre_consult_update')

        # Day 10th
        with patch('django.utils.timezone.now', return_value=timezone.now() + datetime.timedelta(days=10)):
            overdue_workflows = ReferralLawyerWorkflowState.objects.get_overdue_workflows_for_professional(event_type=event_type, professional=lawyer1)
            self.assertEqual(overdue_workflows.count(), 2)
            workflow_ids = [w.id for w in overdue_workflows]
            for workflow in workflows1:
                self.assertIn(workflow.id, workflow_ids)
            for workflow in workflows2:
                self.assertNotIn(workflow.id, workflow_ids)
