![Django Tests](https://github.com/lowbono/lowbono-django/actions/workflows/dokku.yml/badge.svg)

#### Installation:

* Install Python 3.12+ and pip
* `cd` into this directory
* `pip install -r requirements.txt`
* `python manage.py migrate` to create database and apply changes
* `python manage.py createsuperuser` to create admin user

#### Starting Application on Localhost

`python manage.py runserver` to launch django test server at `localhost:8000`

#### Starting Celery Instances

* `cd` to root of the application where manage.py stays
* Use `celery -A lowbono worker --concurrency=5 --beat -S django_celery_beat.schedulers:DatabaseScheduler -l info -Q celery` to start local celery instance

The LLM workflow needs a specialized worker:

* Use `celery -A lowbono worker --concurrency=1 -l info -Q llm_queue`

#### Testing Application

`python manage.py test` to run tests

<br>

#### Configurations & Setup

##### Add staff user

Login as admin or staff, add staff users, allocate various permissions

##### Add/update CMS Pages

Login as admin or staff, and try to create pages like home page, about us, contact, etc. Some pre-built, ready-to-use templates exists in `lowbono_cms/templates` directory, which you can use that covers most of use-cases.

##### Add/update practiceArea model data

Login as admin, and you can add different practiceareas, their categories, descriptions, etc.

Note: Migration at `0002_auto_20260214_0543.py` fills PracticeArea model from taxanomy .csv at available in `lowbono_app/data` module related to Washington DC. You can use those, or delete this file, and create your own from admin dashboard.

##### Add Email Templates & Workflow Events

Add email templates, as well as configure events that triggers them

##### Invite lawyer or mediator type professionals

Send email invites from dashboard, and they can login and configure their profiles, details, practice area categories, etc. You can disable, enable the profiles

##### Configure baseline poverty rates

Easy to update using admin dashboard

##### Onboarding clients

Easy to onboard clients, simple to setup questions, use of AI to match with correct professionals, notificatiosn to both client and professionals once details recieved

##### Automatic follow-ups with professionals

Based on event events, case status, days since last update, system sends personalized, automatted emails 

##### Manage cases

Professionals can close cases, re-open if required, update hours worked, current status, etc for staff to monitor and followup

<br>

#### Advanced: Template & Views Translations for Multi-language setup

##### To Translate

* 'cd' into respective app for which translation needs to be done.
* Run `django-admin makemessages -l es` to generate .po files in app's locale folder. This command scans .html, .txt and .py files for strings to be translated.
* Add translations of respective strings in .po files generated above.
* Run `django-admin compilemessages` to generate .mo binary files.

#### Model Translations

##### To Translate Model Data

Use command `python manage.py translate-models --update` to translate model's column data.

##### How it works

To allow translation of dynamic data from models like `PracticeArea`, we use [Modeltranslation](https://django-modeltranslation.readthedocs.io/en/latest/) library. This library takes care of most use cases, and it's documentation is also highly comprehensive.

To add translation fields in any model, add or update `translation.py` file into app directory and configure model fields.

After this, run `python manage.py makemigrations` and `python manage.py migrate` to generate and apply translation migrations. 

However, the new columns `col_name_en`, `col_name_es` in respective database table would be empty at start.

So, to fill empty language columns, you have two choices:

* You can run `python manage.py update_translation_fields` command to populate new columns from existing values. For example, `title_en` would be populated from `title` column. Note: This pre-population only happens for default language which is first language in `settings.py`'s `LANGUAGES` tuple.
* Use management command `python manage.py translate-models --update` to fill `_es` columns from pre-defined translations available at `lowbono_app/management/commands/models_translation_data.json`. This command also takes care of running above default `update_translation_fields` command to translate default `_en` fields.

Note: `translate-models` command has additional `--generate` flag, to scan respective models for default string values, and then translate them into desired language. Currently, it uses a custom Google Translate script, but it's status is WIP for now, as Google translate is not that effective.
