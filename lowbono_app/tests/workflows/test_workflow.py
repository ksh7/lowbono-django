import datetime

from django.utils import timezone
from django.core import mail
from django.test import TransactionTestCase
from django.urls import reverse

from lowbono_app.models import User, Referral, ReferralSource


class ReferralWorkflowTasksTestCase(TransactionTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

    def setUp(self):
        super().setUp()

        self.professional = User.objects.create(email='a1@dcerefer.org', password='password')
        self.referral_source = ReferralSource.objects.create(source='DC Affordable Law Firm')

        self.referral = Referral.objects.create(professional=self.professional, email='test1@client.com', referred_by=self.referral_source)
