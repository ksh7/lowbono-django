from django.apps import apps
from django.core.mail import send_mail, EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings
from . import models
from . import utils


def send_email(to_email, subject, text_content, html_content, referral_notification_id=None, task_id=None):

    msg = EmailMultiAlternatives(to=[to_email], subject=subject, body=text_content,
                                 from_email=settings.EMAIL_ALIAS, reply_to=[settings.EMAIL_ALIAS])
    msg.attach_alternative(html_content, "text/html")

    notification = models.ReferralNotifications.objects.get(pk=referral_notification_id) if referral_notification_id else None

    try:
        msg_sent = False
        if task_id:
            task = apps.get_model('joeflow', 'Task').objects.get(pk=task_id)
            if task.name == task.workflow.get_current_node_name():
                msg.send()
                msg_sent = True
        else:
            msg.send()
            msg_sent = True

        if notification and msg_sent:
            notification.status = 'SENT'
            notification.save()

    except Exception as e:
        if notification:
            notification.status = 'FAILED'
            notification.save()
        models.EmailAPILogs.objects.create(to_email=to_email, html_content=html_content, api_logs=e)
