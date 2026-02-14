from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import m2m_changed
from phonenumber_field.modelfields import PhoneNumberField

from lowbono_app.models import Referral, Professional, User, BarAdmission, _update_is_profile_complete


class MediatorReferral(models.Model):
    referral = models.OneToOneField(Referral, on_delete=models.CASCADE, blank=False, null=False, related_name='mediator_referral')

    other_party_first_name = models.CharField(_("First Name"), max_length=150, blank=True, null=True)
    other_party_last_name = models.CharField(_("Last Name"), max_length=150, blank=True, null=True)
    other_party_email = models.EmailField(_("Email"), blank=True, null=True)
    other_party_phone = PhoneNumberField(_("Phone"), blank=True, null=True)
    other_party_address = models.TextField(blank=True, null=True, default='')
    other_party_zipcode = models.CharField(max_length=5, blank=True, null=True, default=None)

    def __str__(self):
        return 'Client: ' + self.referral.get_full_name() + ' --> Mediator: ' + self.referral.professional.get_full_name()


class Mediator(Professional):
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=False, null=False, related_name='mediator_user')
    practice_areas = models.ManyToManyField('lowbono_app.PracticeArea', through='lowbono_mediator.MediatorPracticeAreas', related_name='mediator_practiceareas')
    mediation_type = models.ForeignKey("lowbono_mediator.MediationType", on_delete=models.SET_NULL, blank=True, null=True)

    def get_bar_admissions_display(self):
        return [bar.get_bar_admissions_display() for bar in self.user.bar_admissions.all()]

    def get_bar_admissions(self, display=False):
        return list(self.bar_admissions.all().values_list('bar_admission', flat=True))

    def set_bar_admissions(self, bar_admissions):
        bar_admissions = [BarAdmission.objects.get_or_create(state=bar, user=self)[0] for bar in bar_admissions]
        self.bar_admissions.set(bar_admissions)
        return bar_admissions

    def __str__(self):
        return f'{self.__class__.__name__} info for {self.user}'

    def __repr__(self):
        return f'<{self.__str__()}>'


class MediatorPracticeAreas(models.Model):
    mediator = models.ForeignKey(Mediator, on_delete=models.CASCADE)
    practicearea = models.ForeignKey('lowbono_app.PracticeArea', on_delete=models.CASCADE, related_name='mediator_practice_areas')
    approved = models.BooleanField(default=False, blank=False, null=False)

    def __str__(self):
        return f'Practice Areas for {self.mediator.user}'

    def __repr__(self):
        return f'<{self.__str__}>'

m2m_changed.connect(_update_is_profile_complete, sender=Mediator.practice_areas.through)


class MediationType(models.Model):
    name = models.CharField(max_length=64, default='None', choices=[('facilitative', 'Facilitative'), ('evaluative', 'Evaluative'), ('facilitative_and_evaluative', 'Combined (Facilitative & Evaluative)')])
    description = models.CharField(max_length=256, blank=True, default='', null=True)

    class Meta:
        verbose_name = 'MediationType'
        verbose_name_plural = 'MediationTypes'

    def __str__(self):
        return f'{self.name}'

    def __repr__(self):
        return f'<{self.__str__}>'
