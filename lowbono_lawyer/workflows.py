from django.conf import settings
from django.urls import reverse
from joeflow.models import Workflow

from lowbono_app.workflows import ReferralUpdateViewBase, CustomJoeflowStart, ReferralWorkflowStateBase


class ReferralUpdateView(ReferralUpdateViewBase):
    pass


class ReferralLawyerWorkflowState(ReferralWorkflowStateBase, Workflow):

    pretty_nodes = {
        'referral_received': 'Referral Received',
        'waiting_for_first_pre_consult_update': 'Waiting for First Update',
        'waiting_for_pre_consult_update': 'Waiting for Consult',
        'closed_without_consult': 'Closed without Consult',
        'waiting_for_post_engagement_update': 'Consult Held - Engaged',
        'consult_held_closed_without_engagement': 'Consult Held - Closed without Engagement',
        'waiting_for_post_consult_update': 'Consult Held - Waiting for Engagement',
        'engagement_completed': 'Engagement Completed',
    }

    class Meta:
        verbose_name = 'Referral Lawyer Workflow'
        verbose_name_plural = 'Referral Lawyer Workflows'

    @staticmethod
    def is_lawyer_type():
        return True

    @staticmethod
    def is_mediator_type():
        return False

    @staticmethod
    def get_bulk_update_dashboard_link(professional_id, workflow_state):

        return f'{settings.HOST}{reverse("pending-lawyer-matters-by-event", args=[professional_id, workflow_state])}'

    @staticmethod
    def get_pretty_name_for_node(node_name):
        return ReferralLawyerWorkflowState.pretty_nodes.get(node_name, '')

    def save(self, *args, **kwargs):
        """
            this model is updated from two sources i.e.
                - by user via form to provide report statuses
                - by celery tasks while sending email notifications

            method helps maintain state accordingly.
        """

        if self.task_set.count():
            self.current_task = self.task_set.latest()
        if self.is_human_activity:
            self.notification = None
            self.is_overdue = False
        else:
            self.hours_worked = 0
            self.notes = ''
            self.is_overdue = True
        return super().save(*args, **kwargs)


    # start workflow
    referral_received = CustomJoeflowStart()

    # human tasks
    waiting_for_first_pre_consult_update = ReferralUpdateView()
    waiting_for_pre_consult_update = ReferralUpdateView()
    waiting_for_post_consult_update = ReferralUpdateView()
    waiting_for_post_engagement_update = ReferralUpdateView()

    def engagement_completed(self):
        pass

    def closed_without_consult(self):
        pass

    def consult_held_closed_without_engagement(self):
        pass

    # edges for joeflow transition
    edges = [
        (referral_received, waiting_for_first_pre_consult_update),

        (waiting_for_first_pre_consult_update, waiting_for_pre_consult_update),
        (waiting_for_first_pre_consult_update, waiting_for_post_consult_update),
        (waiting_for_first_pre_consult_update, waiting_for_post_engagement_update),
        (waiting_for_first_pre_consult_update, consult_held_closed_without_engagement),
        (waiting_for_first_pre_consult_update, closed_without_consult),
        (waiting_for_first_pre_consult_update, engagement_completed),

        (waiting_for_pre_consult_update, waiting_for_pre_consult_update),
        (waiting_for_pre_consult_update, waiting_for_post_consult_update),
        (waiting_for_pre_consult_update, waiting_for_post_engagement_update),
        (waiting_for_pre_consult_update, consult_held_closed_without_engagement),
        (waiting_for_pre_consult_update, closed_without_consult),
        (waiting_for_pre_consult_update, engagement_completed),

        (waiting_for_post_consult_update, waiting_for_post_consult_update),
        (waiting_for_post_consult_update, waiting_for_post_engagement_update),
        (waiting_for_post_consult_update, consult_held_closed_without_engagement),
        (waiting_for_post_consult_update, engagement_completed),

        (waiting_for_post_engagement_update, waiting_for_post_engagement_update),
        (waiting_for_post_engagement_update, engagement_completed),
    ]
