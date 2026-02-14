import re
import random
import urllib.request
import urllib.parse
import datetime
import redis
import logging

from django.template import Context, Template
from django.utils import timezone
from bs4 import BeautifulSoup

from faker import Faker

from lowbono.settings import REDIS_CONNECTION_URL

from . import models

fake = Faker()

logger_joeflow = logging.getLogger('joeflow_log')


def redis_status_log(failed_at=0):
    conn = redis.from_url(REDIS_CONNECTION_URL)
    try:
        conn.ping()
    except:
        logger_joeflow.warning("Redis not available at: %s and failed at checkpoint: %d" % (datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S:%f'), failed_at))

def translate_using_google(from_lang='en', to_lang=None, translate_str=None):
    """
        Custom wrapper around https://translate.google.com that gets translation done using URL
        and then parses the returned HTML to find translated string.

        params:
            from_lang: short code like 'en' for base language, auto-detects if not supplied
            to_lang: short code like 'es' for langauge to which translation is done
            translate_str: base language string to be translated
    """

    if not to_lang or not translate_str:
        return ""

    agent = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X x.y; rv:42.0) Gecko/20100101 Firefox/42.0"}

    base_link = "https://translate.google.com/m?tl=%s&sl=%s&q=%s"
    translate_str = urllib.parse.quote(translate_str)
    link = base_link % (to_lang, from_lang, translate_str)
    request = urllib.request.Request(link, headers=agent)

    raw_data = urllib.request.urlopen(request).read()
    data = raw_data.decode("utf-8")
    expr = r'(?s)class="(?:t0|result-container)">(.*?)<'
    re_result = re.findall(expr, data)

    result = re_result[0] if len(re_result) > 0 else ""

    return result


def filterLawyers(practice_area_category=None, practice_area=None):
    """
    Gets lawyer practice area requirements from steps flow
    Returns list of available lawyers
    """

    from lowbono_lawyer.models import Lawyer
    lawyers = Lawyer.objects.get_lawyer_matches(practice_area)

    lawyer_list = []
    for lawyer in lawyers:
        lawyer_list.append((lawyer.user.id, lawyer.user))

    random.shuffle(lawyer_list)
    return lawyer_list


def filterMediators(practice_area_category=None, practice_area=None):
    """
    Gets lawyer practice area requirements from steps flow
    Returns list of available lawyers
    """

    from lowbono_mediator.models import Mediator
    mediators = Mediator.objects.get_mediator_matches(practice_area)

    mediator_list = []
    for mediator in mediators:
        mediator_list.append((mediator.user.id, mediator.user))

    random.shuffle(mediator_list)
    return mediator_list


def generateSystemEmailTemplates(system_email_event, template_vars):
    """
    Gets template details from database and generates text/html template content
    """

    _instance = models.SystemEmailEvents.objects.get(event_name=system_email_event).template

    subject = Template(_instance.subject).render(Context(template_vars))
    html_content = Template(_instance.body).render(Context(template_vars))
    text_content = BeautifulSoup(html_content, features="html.parser").get_text()

    return subject, text_content, html_content


def get_dummy_data(var):
    if 'name' in var:
        return fake.name()
    if 'link' in var or 'url' in var:
        return 'https://lowbono.org/sample-url'
    if 'duration' in var:
        return 3
    if 'date' in var or 'deadline' in var:
        return datetime.datetime.today().strftime("%d %b %Y")
    if 'status' in var:
        return 'RANDOM-STATUS'
    if 'email' in var:
        return 'a1@lowbono.org'
    if 'phone' in var:
        return '(000) 000-0000'

    return 'NO VALUE'


def generateViewEmailTemplate(template_id):
    """
    Generates dummy view for template
    """

    _instance = models.EmailTemplates.objects.get(id=template_id)
    html_template = Template(_instance.body)

    template_vars = []
    for temp in html_template.nodelist:
        if 's' not in dir(temp):
            template_vars.append(temp.token.contents)

    template_vars =  list(set(template_vars))

    sample_template_vars = {}
    for var in list(set(template_vars)):
        sample_template_vars[var] = get_dummy_data(var.lower())

    html_content = html_template.render(Context(sample_template_vars))

    return html_content


def pretty_date_email_template(date_obj):
    """Convert a datetime object to a human-readable relative time string."""
    if date_obj is None:
        return 'Never Updated'

    if isinstance(date_obj, datetime.datetime):
        time_diff = timezone.now() - date_obj
        if time_diff > datetime.timedelta(days=30):
            return date_obj.strftime("%b %d, %Y")
        return "Recently Updated" if time_diff.days < 3 else f"{time_diff.days} days ago"
    return date_obj
