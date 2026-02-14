from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import m2m_changed

from lowbono_app.models import Referral, Professional, User, BarAdmission, LLMLogs, _update_is_profile_complete


class LawyerReferral(models.Model):
    referral = models.OneToOneField(Referral, on_delete=models.CASCADE, blank=False, null=False, related_name='lawyer_referral')

    def __str__(self):
        return 'Client: ' + self.referral.get_full_name() + ' --> Lawyer: ' + self.referral.professional.get_full_name()


class Lawyer(Professional):
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=False, null=False, related_name='lawyer_user')
    practice_areas = models.ManyToManyField('lowbono_app.PracticeArea', through='lowbono_lawyer.LawyerPracticeAreas', related_name='lawyer_practiceareas')

    def get_bar_admissions_display(self):
        return [bar.get_bar_admissions_display() for bar in self.user.bar_admissions.all()]

    def get_bar_admissions(self, display=False):
        return list(self.bar_admissions.all().values_list('bar_admission', flat=True))

    def set_bar_admissions(self, bar_admissions):
        bar_admissions = [BarAdmission.objects.get_or_create(state=bar, user=self)[0] for bar in bar_admissions]
        self.bar_admissions.set(bar_admissions)
        return bar_admissions

    def _is_profile_complete(self):
        return bool(super()._is_profile_complete() and bool(self.user.bar_admissions.count()))

    def __str__(self):
        return f'{self.__class__.__name__} info for {self.user}'

    def __repr__(self):
        return f'<{self.__str__()}>'


class LawyerPracticeAreas(models.Model):
    lawyer = models.ForeignKey(Lawyer, on_delete=models.CASCADE)
    practicearea = models.ForeignKey('lowbono_app.PracticeArea', on_delete=models.CASCADE, related_name='lawyer_practice_areas')
    approved = models.BooleanField(default=False, blank=False, null=False)

    def __str__(self):
        return f'Practice Areas for {self.lawyer.user}'

    def __repr__(self):
        return f'<{self.__str__}>'


m2m_changed.connect(_update_is_profile_complete, sender=Lawyer.practice_areas.through)


class LawyerLLMLogs(LLMLogs):
    """ stores Lawyer LLM logs """

    lawyer_referral = models.ForeignKey(LawyerReferral, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name = 'Lawyer LLM Logs'
        verbose_name_plural = 'Lawyer LLM Logs'
