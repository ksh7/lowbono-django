import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from django.conf import settings


def send_slack_alert(channel, message):
    client = WebClient(token=settings.SLACK_BOT_OAUTH_TOKEN)
    try:
        client.chat_postMessage(channel=channel, text=message)
    except SlackApiError as e:
        pass
