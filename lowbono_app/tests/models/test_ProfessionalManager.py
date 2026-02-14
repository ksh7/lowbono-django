from django.test import TestCase, TransactionTestCase
from lowbono_app.tests.utils import create_user, create_practice_area
from lowbono_app.models import Vacation
from lowbono_lawyer.models import Lawyer, LawyerPracticeAreas
from datetime import date


class ProfessionalManagerTestCase(TestCase):
    def test_practices_in_WHERE_professional_has_practice_area_EXPECT_professional_returned_WHEN_approved_is_true(self):
        practice_area = create_practice_area()
        _, professional, _ = create_user('jdoe@example.com', lawyer_kwargs={'practice_areas': [practice_area]})
        LawyerPracticeAreas.objects.create(lawyer=professional, practicearea=practice_area, approved=True)

        cut = Lawyer.objects.practices_in

        actual = cut(practice_area, 'lawyer')
        expected = [professional]
        self.assertEqual(list(actual), expected)

    def test_practices_in_WHERE_professional_has_practice_area_EXPECT_professional_not_returned_WHEN_approved_is_false(self):
        practice_area = create_practice_area()
        _, professional, _ = create_user('jdoe@example.com', lawyer_kwargs={'practice_areas': [practice_area]})
        LawyerPracticeAreas.objects.create(lawyer=professional, practicearea=practice_area, approved=False)

        cut = Lawyer.objects.practices_in

        actual = cut(practice_area, 'lawyer')
        expected = []
        self.assertEqual(list(actual), expected)

    def test_practices_in_WHERE_professional_has_parent_practice_area_EXPECT_professional_returned_WHEN_approved_is_true(self):
        practice_area = create_practice_area()

        _, professional, _ = create_user('jdoe@example.com', lawyer_kwargs={'practice_areas': [practice_area]})
        LawyerPracticeAreas.objects.create(lawyer=professional, practicearea=practice_area, approved=True)

        cut = Lawyer.objects.practices_in
        actual = cut(practice_area, 'lawyer')
        expected = [professional]
        self.assertEqual(list(actual), expected)

    def test_practices_in_WHERE_professional_has_parent_practice_area_EXPECT_professional_not_returned_WHEN_approved_is_false(self):
        practice_area = create_practice_area()

        _, professional, _ = create_user('jdoe@example.com', lawyer_kwargs={'practice_areas': [practice_area]})
        LawyerPracticeAreas.objects.create(lawyer=professional, practicearea=practice_area, approved=False)

        cut = Lawyer.objects.practices_in
        actual = cut(practice_area, 'lawyer')
        expected = []
        self.assertEqual(list(actual), expected)

    def test_practices_in_WHERE_professional_does_not_have_practice_area_EXPECT_professional_not_returned(self):
        practice_area = create_practice_area()
        other_practice_area = create_practice_area()

        _, professional, _ = create_user('jdoe@example.com', lawyer_kwargs={'practice_areas': [other_practice_area]})

        cut = Lawyer.objects.practices_in
        actual = cut(practice_area, 'lawyer')
        expected = []
        self.assertEqual(list(actual), expected)

    vacation_tests = (
        # first_day in days relative to today, last_day in days relative to today (None for no last_day), expected, explanation
        # (-1, None, True, 'if first_day is before today, and there is no last_day, then EXPECT on vacation'),
        (-1, 0, True, 'if first_day is before today, and last_day is on today, then EXPECT on vacation'),
        # (0, None, True, 'if first_day is on today, and there is no last_day, then EXPECT on vacation'),
        (0, +1, True, 'if first_day is on today, and last_day is after today, then EXPECT on vacation'),
        (0, 0, True, 'if first_day is on today, and last_day is on today, then EXPECT on vacation'),
        (+1, None, False, 'if first_day is after today, and last_day is None, then EXPECT off vacation'),
        (+1, +2, False, 'if first_day is after today, and last_day is after today, then EXPECT off vacation'),
        (-2, -1, False, 'if first_day is before today, and last_day is before today, then EXPECT off vacation'),
    )

    def test_is_on_vacation(self):

        today = date(2020, 1, 15)
        user, professional, _ = create_user('jdoe@example.com', lawyer_kwargs={})

        for first_day, last_day, expected, explanation in self.vacation_tests:
            if first_day is not None:
                first_day = date(2020, 1, 15 + first_day)
            if last_day is not None:
                last_day = date(2020, 1, 15 + last_day)

            with self.subTest(first_day=first_day, last_day=last_day, expected=expected, explanation=explanation):
                vacation = Vacation(user=user, first_day=first_day, last_day=last_day)
                vacation.save()

                cut = Lawyer.objects.is_on_vacation

                actual = professional in cut(_date=today)

                self.assertEqual(actual, expected)

                user.vacations.all().delete()

    def test_is_working(self):

        today = date(2020, 1, 15)
        user, professional, _ = create_user('jdoe@example.com', lawyer_kwargs={})

        for first_day, last_day, expected, explanation in self.vacation_tests:
            if first_day is not None:
                first_day = date(2020, 1, 15 + first_day)
            if last_day is not None:
                last_day = date(2020, 1, 15 + last_day)

            expected = not expected

            with self.subTest(first_day=first_day, last_day=last_day, expected=expected, explanation=explanation):
                vacation = Vacation(user=user, first_day=first_day, last_day=last_day)
                vacation.save()

                cut = Lawyer.objects.is_working

                actual = professional in cut(_date=today)

                self.assertEqual(actual, expected)

                user.vacations.all().delete()
