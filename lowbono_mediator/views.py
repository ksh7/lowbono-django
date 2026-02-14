from django.contrib import messages
from datetime import datetime, timedelta

from django.shortcuts import render, redirect
from django.http import HttpResponseNotFound, HttpResponse
from django.template.loader import render_to_string
from django.contrib.contenttypes.models import ContentType
from lowbono_app.models import EmailEventInactiveFor, User

from . import steps


def step(request, step):
    StepView = getattr(steps, f'Step{step}View', None)
    if StepView is None:
        return HttpResponseNotFound('Not a valid step')
    return StepView.as_view()(request)


def overdueMattersEmail(request, professional_id, workflow_state):

    if request.user.id != int(professional_id) and not request.user.is_staff:
        messages.info(request, 'Oops, you can\'t access this page.')
        return redirect('dashboard')

    from .workflows import ReferralMediatorWorkflowState

    professional = User.objects.get(id=professional_id)
    content_type = ContentType.objects.get_for_model(ReferralLawyerWorkflowState)
    event_type = EmailEventInactiveFor.objects.filter(workflow_state=workflow_state, template__workflow_type=content_type).first()

    context = {}
    context['current_node_pretty_name'] = ReferralLawyerWorkflowState.get_pretty_name_for_node(workflow_state)
    context['overdue_matters'] = ReferralLawyerWorkflowState.objects.get_overdue_referrals_for_professional(event_type, professional)
    return render(request, 'lowbono_mediator/pending_referrals_list.html', context)


def updateMediatorReferralWorkflow(request):
    if request.htmx:
        from .workflows import ReferralMediatorWorkflowState
        referralmediatorworkflowstate = ReferralMediatorWorkflowState.objects.get(id=request.GET["workflow_id"])
        if referralmediatorworkflowstate:
            referralmediatorworkflowstate.is_human_activity = True
            referralmediatorworkflowstate.save()

            return HttpResponse(render_to_string('lowbono_mediator/_htmx_pending_referral_row.html', {'referral': referralmediatorworkflowstate.referral}))

    return None
