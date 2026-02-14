from django.contrib import messages
from datetime import datetime, timedelta

from django.shortcuts import render, redirect
from django.http import HttpResponseNotFound, HttpResponse
from django.template.loader import render_to_string
from django.contrib.contenttypes.models import ContentType

from lowbono_app.models import EmailEventInactiveFor, User

from . import steps

from celery.result import AsyncResult


def step(request, step):
    StepView = getattr(steps, f'Step{step}View', None)
    if StepView is None:
        return HttpResponseNotFound('Not a valid step')
    return StepView.as_view()(request)


def llmAwait(request):
    step_data = request.session.get('step_data', {})
    task_id = step_data.get('llm_decision_task_id')
    if task_id:
        task = AsyncResult(task_id)
        if task.ready():
            result = task.result
            if task.state == "SUCCESS" and result:
                return redirect(result)
            messages.info(request, 'There was an issue automatically categorizing your legal issue by our AI. Please proceed by selecting manually or try again later.')
            return redirect('lawyer_step', step=6)
    else:
        return HttpResponseNotFound('Not a valid step')

    llm_decision_task_start_time = datetime.strptime(step_data.get('llm_decision_task_start_time'), "%Y-%m-%d %H:%M:%S.%f")
    if datetime.now() - llm_decision_task_start_time > timedelta(seconds=20):
        messages.info(request, 'There was an issue automatically categorizing your legal issue by our AI. Please proceed by selecting manually or try again later.')
        return redirect('lawyer_step', step=6)
    return render(request, 'lowbono_app/llm_await.html')


def overdueMattersEmail(request, professional_id, workflow_state):

    if request.user.id != int(professional_id) and not request.user.is_staff:
        messages.info(request, 'Oops, you can\'t access this page.')
        return redirect('dashboard')

    from .workflows import ReferralLawyerWorkflowState

    professional = User.objects.get(id=professional_id)
    content_type = ContentType.objects.get_for_model(ReferralLawyerWorkflowState)
    event_type = EmailEventInactiveFor.objects.filter(workflow_state=workflow_state, template__workflow_type=content_type).first()

    context = {}
    context['current_node_pretty_name'] = ReferralLawyerWorkflowState.get_pretty_name_for_node(workflow_state)
    context['overdue_matters'] = ReferralLawyerWorkflowState.objects.get_overdue_referrals_for_professional(event_type, professional)
    return render(request, 'lowbono_lawyer/pending_referrals_list.html', context)


def updateLawyerReferralWorkflow(request):
    if request.htmx:
        from .workflows import ReferralLawyerWorkflowState
        referrallawyerworkflowstate = ReferralLawyerWorkflowState.objects.get(id=request.GET["workflow_id"])
        if referrallawyerworkflowstate:
            referrallawyerworkflowstate.is_human_activity = True
            referrallawyerworkflowstate.save()

            return HttpResponse(render_to_string('lowbono_lawyer/_htmx_pending_referral_row.html', {'referral': referrallawyerworkflowstate.referral}))

    return None
