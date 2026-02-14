import os

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def handle(self, *args, **options):
        print('Resetting development database with dummy data...')

        call_command('migrate')

        call_command('translate-models', '--update')
        call_command('loaddata', 'sample-admin-user')
        call_command('loaddata', 'cms-sites')
