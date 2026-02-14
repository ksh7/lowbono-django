from django.test import TestCase
from lowbono_app.tests.utils import create_user, create_practice_area, get_complete_kwargs
from lowbono_mediator.models import Mediator


class MediatorTestCase(TestCase):
    def test__is_profile_complete_WHEN_profile_complete_EXPECT_true(self):
        _, _, mediator = create_user('jdoe@example.com', **get_complete_kwargs())

        cut = mediator._is_profile_complete
        actual = cut()
        self.assertTrue(actual)

    def test__is_profile_complete_WHEN_profile_incomplete_EXPECT_false(self):
        practice_area = create_practice_area()

        complete_kwargs = get_complete_kwargs(practice_area)['mediator_kwargs']
        for k in complete_kwargs:
            with self.subTest(missing_key=k):
                partial_kwargs = get_complete_kwargs(practice_area=practice_area)
                partial_kwargs['mediator_kwargs'].pop(k)
                user, _, partial_mediator = create_user('jdoe@example.com', **partial_kwargs)

                cut = partial_mediator._is_profile_complete
                actual = cut()
                self.assertFalse(actual)

                user.delete()

    def test_is_profile_complete_WHEN_practice_area_updated_EXPECT_is_profile_complete_updated(self):
        practice_area = create_practice_area()

        partial_kwargs = get_complete_kwargs(practice_area)
        missing_data = partial_kwargs['mediator_kwargs'].pop('practice_areas')

        _, _, mediator = create_user('jdoe@example.com', **partial_kwargs)

        actual = mediator.is_profile_complete
        self.assertFalse(actual)

        mediator.practice_areas.set(missing_data)
        mediator.save()

        actual = Mediator.objects.get(id=mediator.id).is_profile_complete
        self.assertTrue(actual)
