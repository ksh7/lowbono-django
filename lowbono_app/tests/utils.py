from lowbono_app.models import BarAdmission, User, PracticeAreaCategory, PracticeArea, Referral, ReferralSource, Vacation, Token
from lowbono_lawyer.models import Lawyer
from lowbono_mediator.models import Mediator


def _update_model_with_dict(model_instance, data_dict):
    for attr, val in data_dict.items():
        try:
            setattr(model_instance, attr, val)
        except TypeError as e:
            if e.args and e.args[0].startswith('Direct assignment'):
                getattr(model_instance, attr).set(val)
            else:
                raise e
    model_instance.save()
    return model_instance


def create_user(email, password=None, user_kwargs=None, bar_admission_kwargs=None, lawyer_kwargs=None, mediator_kwargs=None):
    """
    Quickly create a new user.
    """

    user = User.objects.create_user(email, password)
    if user_kwargs is not None:
        user = _update_model_with_dict(user, user_kwargs)

    if bar_admission_kwargs is not None:
        bar_admission_kwargs['user'] = user
        bar_admission = BarAdmission(**bar_admission_kwargs)
        bar_admission.save()

    lawyer = None
    if lawyer_kwargs is not None:
        lawyer = Lawyer(user=user)
        lawyer.save()
        lawyer = _update_model_with_dict(lawyer, lawyer_kwargs)

    mediator = None
    if mediator_kwargs is not None:
        mediator = Mediator(user=user)
        mediator.save()
        mediator = _update_model_with_dict(mediator, mediator_kwargs)

    return user, lawyer, mediator


def create_practice_area():
    out = _create_one_practice_area()
    return out


def get_complete_kwargs(practice_area=None):
    practice_area = practice_area or create_practice_area()
    return {
        'user_kwargs': {
            'first_name': 'John',
            'last_name': 'Doe',
            'firm_name': 'Doe and Associates',
            'phone': '202-555-1234',
            'address': '123 Main St\nWashington, DC 20006',
            'photo': 'test.jpg',
            'bio': 'Lorem ipsum dolor sit amet.',
        },
        'bar_admission_kwargs': {
            'state': 'CA',
            'admission_date': '2010-01-01'
        },
        'lawyer_kwargs': {
            'practice_areas': [practice_area],
        },
        'mediator_kwargs': {
            'practice_areas': [practice_area],
        },
    }


def _create_one_practice_area():
    parent, _ = PracticeAreaCategory.objects.get_or_create(id=1, defaults={'title': _lorem(10), 'definition': _lorem()})
    out, _ = PracticeArea.objects.get_or_create(id=1, defaults={'title': _lorem(10), 'definition': _lorem(), 'parent': parent})
    return out


def _lorem(length=0):
    lorem = 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.'.split()
    if length:
        lorem = lorem[:length]
    return ' '.join(lorem)


def create_referral(user, email='sample@email.com'):
    """
        Create referral object
    """

    referral_source, _ = ReferralSource.objects.get_or_create(source='Web search')

    referral, _ = Referral.objects.get_or_create(professional=user,
                                                 first_name='Jon',
                                                 last_name='Doe',
                                                 email=email,
                                                 deadline_date='2022-05-05',
                                                 referred_by=referral_source)

    return referral


def create_vacation(user):
    """
        Create vacation object
    """

    vacation, _ = Vacation.objects.get_or_create(user=user, first_day='2022-05-10', last_day='2022-05-20')

    return vacation


def create_user_via_invite(email, password=None):
    """
        Invite a user
    """

    user, _, _ = create_user(email, password)
    lawyer, _ = Lawyer.objects.get_or_create(user=user)
    token, _ = Token.objects.get_or_create(user=user)

    return user
