from django.test import TestCase
from unittest.mock import patch

class LLMTestCase(TestCase):
    fixtures = ['admin-user', 'group-permissions', 'sample-data-temp'] #, 'pages', 'cms-sites', 'cms-plugins',]

    def test_anonymize_text(self):
        from lowbono_app.tasks import anonymize_text
        test_input = "My name is Andrew Smith and you can call me at 555-123-1234"
        anonymized_text = anonymize_text(test_input)
        self.assertEqual(anonymized_text, "My name is <PERSON> and you can call me at <PHONE_NUMBER>")

    def test_create_prompt(self):
        """This is merely a smoke test to ensure the method works."""
        from lowbono_app.tasks import create_prompt, get_practice_areas
        from lowbono_lawyer.models import Lawyer
        prompt = create_prompt(get_practice_areas(Lawyer))
        self.assertIsInstance(prompt, str)

    def test_llm(self):
        from lowbono_app.models import PracticeArea
        from lowbono_app.tasks import llm_categorize_description
        practice_area = PracticeArea.objects.first()
        with patch('lowbono_app.tasks.query_openai') as mock_task:
            mock_task.return_value = (practice_area, None)
            result = llm_categorize_description('fake_key', 'lorem ipsum', 'return_nonce')
            self.assertEqual(result, 'return_nonce')

