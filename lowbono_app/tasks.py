import datetime
from importlib import import_module
import inspect
import json
import string
import time

from itertools import groupby
from operator import attrgetter

from django.db.models import Q
from django.utils import timezone
from django.conf import settings
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

import requests

from lowbono_app.emails import send_email

import logging

logger_joeflow = logging.getLogger('joeflow_log')
logger_llm = logging.getLogger('llm_log')

@shared_task(name="celery_health_heartbeat")
def celery_health_heartbeat():
    """ GET request on BetterUpTime URL to ensure Celery is up and running. """

    requests.get(settings.BETTER_UPTIME_CELERY_HEARTBEAT_URL)

    return True


@shared_task(name="dispatch_email_via_api")
def dispatch_email_via_api(to_email, subject, text_content, html_content, referral_notification_id=None, task_id=None):
    send_email(to_email=to_email, subject=subject, text_content=text_content, html_content=html_content,
               referral_notification_id=referral_notification_id, task_id=task_id)

    return True


@shared_task(name="send_scheduled_notification_emails")
def send_scheduled_notification_emails():
    """ Sends regular notifications based on Referral Workflow's state. """

    from lowbono_app.models import EmailEventInactiveFor

    for event in EmailEventInactiveFor.objects.all():
        event.send_overdue_notification_to_professionals()

    return True


@shared_task(name="emailtemplates_delayed_send_email")
def emailtemplates_delayed_send_email(workflow_id, template_id, task_id):
    """ Sends an email for a referral based on ETA and current workflow_state"""

    from lowbono_app.models import EmailTemplates
    template = EmailTemplates.objects.get(pk=template_id)

    referral_workflow = template.workflow_type.model_class().objects.get(id=workflow_id)
    required_workflow_state = getattr(template, template.event_type).workflow_state if hasattr(template, template.event_type) else None

    if referral_workflow.get_current_node_name() == required_workflow_state:
        template.send_email(referral_workflow.referral, task_id=task_id)

    return True


@shared_task(name="send_scheduled_eta_emails")
def send_scheduled_eta_emails():
    """ Sends emails with ETA for CeleryETATasks """

    from lowbono_app.models import CeleryETATasks

    for _task in CeleryETATasks.objects.filter(status='SCHEDULED').filter(eta__lt=datetime.datetime.now()):

        try:
            func = globals()[_task.func]
            required_args = inspect.signature(func).parameters.keys()
            result = func(**{arg: _task.args[arg] for arg in required_args}) # unpack required argument values and call function

            if result:
                _task.status = 'DELIVERED'
                _task.save()
        except Exception as e:
            _task.status = 'FAILED'
            _task.error_log = e
            _task.save()


@shared_task(name="initiate_missing_workflows")
def initiate_missing_workflows():
    """ Initiate missing workflows: If a referral was created with no ReferralWorkflowState instance or initial emails sent """

    from datetime import datetime, timedelta
    from lowbono_app.pluggable_app import PluggableApp

    for app in PluggableApp().get_apps():
        for _referral in app._models.Referral.objects.filter(**{f"referral__{app._models.ReferralWorkflowState._meta.model_name}__isnull": True}) \
                                                     .filter(referral__created_at__range=(datetime.now() - timedelta(hours=24), datetime.now() - timedelta(hours=1))):
            app._models.ReferralWorkflowState.referral_received(referral=_referral.referral)
            logger_joeflow.warning("%s started manually for referral ID: %d at: %s" % (app._models.ReferralWorkflowState, _referral.referral.id, datetime.now()))

    return True


def anonymize_text(text):
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    analyzer = AnalyzerEngine()
    # See https://microsoft.github.io/presidio/supported_entities/ for supported entities
    analyzer_results = analyzer.analyze(
        text = text,
        entities = [
            "PHONE_NUMBER",
            "CREDIT_CARD",
            "EMAIL_ADDRESS",
            "PERSON",
            "PHONE_NUMBER", 
            "US_BANK_NUMBER",
            "US_DRIVER_LICENSE",
            "US_ITIN",
            "US_PASSPORT",
            "US_SSN",
        ],
        language = "en",
    )

    anonymizer = AnonymizerEngine()
    anonymized_text = anonymizer.anonymize(text=text, analyzer_results=analyzer_results)
    return anonymized_text.text


def get_practice_areas(practicearea_type_model):
    from lowbono_app.models import PracticeArea
    from django.contrib.contenttypes.models import ContentType
    practicearea_type = ContentType.objects.get_for_model(practicearea_type_model)
    practice_areas = PracticeArea.objects.filter(
        practicearea_type = practicearea_type,
    )
    return practice_areas


def create_prompt(practice_areas):
    prompt_template = """
    I want you to categorize a legal problem. After I describe the legal problem,
    please tell me which category it falls into. Category details are given in a
    list of dictionaries having key/values like 'category_id', 'main_category',
    'category', 'description' as follows:

    {}

    For the given legal issue, please scan through all items of above list and see
    if my legal issue belongs to any category (including its main category and
    description).

    Please respond only with one category_id which is most relevant.
    """.strip()

    data = []
    for pa in practice_areas:

        _description = pa.definition
        if pa.append_to_llm_definition:
            _description = f"{_description}  {pa.append_to_llm_definition}"
        if pa.alternative_to_llm_definition:
            _description = pa.alternative_to_llm_definition

        _pa = {'category_id': pa.pk, 'main_category': pa.parent.title, 'category': pa.title, 'description': _description}

        if pa.title.lower() == 'other':
            _pa['default'] = True
            _pa['description'] = f"{pa.parent.title} law related issues that does not fall into following categories: {', '.join(p.title for p in pa.parent.children.exclude(title='Other'))}"

        data.append(_pa)

    prompt = prompt_template.format(json.dumps(data))
    return prompt


def query_openai(practice_areas, system_content, user_content, llm_logs):
    """Send request to API and extract result as a matching Practice Area."""
    from openai import OpenAI
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY,
    )

    llm_response = ''
    try:
        response = client.responses.create(
            model=settings.OPENAI_MODEL,
            instructions=system_content,
            input=user_content,
        )
        llm_response = response.output_text
    except Exception as e:
        llm_logs.append_to_audit_trail("Warning: Failed to create client in query_openai: %s" % str(e))
        return None, True

    llm_logs.append_to_audit_trail("Result from query_openai: %s" % str(llm_response))
    if llm_response:
        matchable = ''.join(c for c in llm_response if c in string.digits)
        # practice_area.pk are strings, even though they look like numbers
        for practice_area in practice_areas:
            if practice_area.pk == matchable:
                llm_logs.llm_result = "Practice Area: \"%s\" (ID: %s) in \"%s\" category" % (practice_area.title, practice_area.pk, practice_area.parent.title)
                return practice_area, False
    llm_logs.append_to_audit_trail("Warning: No choices returned from api in query_openai")
    return None, True



@shared_task(name="llm.categorize_description", soft_time_limit=20)
def llm_categorize_description(session_key, description, redirect_url):
    """ Anonymize and call OpenAI to categorize description. """
    from lowbono_lawyer.models import Lawyer, LawyerLLMLogs
    SessionStore = import_module(settings.SESSION_ENGINE).SessionStore
    session = SessionStore(session_key=session_key)
    practice_areas = get_practice_areas(Lawyer)
    prompt = create_prompt(practice_areas)

    llm_logs = LawyerLLMLogs.objects.create(user_query=description, instruction_prompt=prompt)

    try:
        start_time = time.time()
        llm_logs.append_to_audit_trail("About to start anonymizing text")
        anonymized_text = anonymize_text(description)
        llm_logs.user_prompt = anonymized_text
        llm_logs.append_to_audit_trail("Anonymization of text done in %s seconds" % str(time.time() - start_time))
        llm_logs.append_to_audit_trail("About to call query_openai with anonymized text: %s" % anonymized_text)
        practice_area, error = query_openai(practice_areas, prompt, anonymized_text, llm_logs)
        llm_logs.append_to_audit_trail("LLM result completed in %s seconds" % str(time.time() - start_time))
    except SoftTimeLimitExceeded:
        llm_logs.append_to_audit_trail("Warning: Timeout on LLM due to exceeding soft_time_limit")
        return None
    except Exception as e:
        llm_logs.append_to_audit_trail("Warning: Exception from query_openai: %s" % str(e))
        raise

    if error:
        return None
    else:
        step_data = session.get('step_data', {})
        step_data['llm_decision'] = True

        step_data['practice_area_category'] = practice_area.parent_id
        step_data['practice_area'] = practice_area.pk
        step_data['lawyer_llm_logs'] = llm_logs.pk
        llm_logs.practice_area_matched_id = practice_area.pk

        session.save()

    llm_logs.save()
    return redirect_url
