from django.test import TestCase
from lowbono_app.tests.utils import create_user, create_practice_area, get_complete_kwargs
from lowbono_app.models import User
from django.test import tag


class UserTestCase(TestCase):

    def test__is_profile_complete_WHEN_profile_complete_EXPECT_true(self):
        user, _, _ = create_user('jdoe@example.com', **get_complete_kwargs())

        cut = user._is_profile_complete
        actual = cut()
        self.assertTrue(actual)

    def test__is_profile_complete_WHEN_profile_incomplete_EXPECT_false(self):
        practice_area = create_practice_area()

        complete_kwargs = get_complete_kwargs(practice_area)['user_kwargs']
        for k in complete_kwargs:
            with self.subTest(missing_key=k):
                partial_kwargs = get_complete_kwargs(practice_area=practice_area)
                partial_kwargs['user_kwargs'].pop(k)
                partial_user, _, _ = create_user('jdoe@example.com', **partial_kwargs)

                cut = partial_user._is_profile_complete
                actual = cut()
                self.assertFalse(actual)

                partial_user.delete()

    def test_is_profile_complete_WHEN_user_updated_EXPECT_is_profile_complete_updated(self):
        practice_area = create_practice_area()

        partial_kwargs = get_complete_kwargs(practice_area)
        missing_data = partial_kwargs['user_kwargs'].pop('address')

        user, _, _ = create_user('jdoe@example.com', **partial_kwargs)

        actual = user.is_profile_complete
        self.assertFalse(actual)

        user.address = missing_data
        user.save()

        actual = user.is_profile_complete
        self.assertTrue(actual)

    def test_raise_value_error_if_email_not_available_on_user_creation(self):
        with self.assertRaises(ValueError) as e:
            user, _, _ = create_user(email='')

        self.assertEqual(str(e.exception), 'Users must have an Email address')
