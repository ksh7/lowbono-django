import json
from pathlib import Path
from django.conf import settings
from django.db.models import Q
from django.core.management import call_command
from django.core.management.base import BaseCommand

from modeltranslation.translator import translator
from lowbono_app.utils import translate_using_google


DIR = Path(__file__).parent
JSON_FILE = DIR / 'models_translation_data.json'


class Command(BaseCommand):
    help = f'translate models'

    def add_arguments(self, parser):
        parser.add_argument('--generate', action='store_true', help='generate',)
        parser.add_argument('--update', action='store_true', help='update',)
        parser.add_argument('--all', action='store_true', help='all',)

    def handle(self, *args, **options):
        """
            Set of methods to load/update translatable data
        """

        call_command('update_translation_fields')  # Modeltranslation's default command

        def get_translation_langauges():
            """
                gets allowed translation languages, ignores default one
                returns: list of languages
            """
            return [lang[0] for lang in settings.LANGUAGES[1:]]

        def generate_translation_strings_file_from_model():
            """
                Read existing .json file for key:value pairs
                Loop through all translator registered model to see if any new rows are available
                For new strings fetched, translate them to desired language using API
                Append new rows key:value and dump new json into the file for future use
            """

            json_data = {}
            with open(JSON_FILE, "r") as outfile:
                json_data = json.load(outfile)

            translation_languages = get_translation_langauges()
            all_values = []
            for model in translator.get_registered_models():
                field_names = translator.get_options_for_model(model).get_field_names()

                for model_object in model.objects.all():
                    for name in field_names:
                        all_values.append(getattr(model_object, name))

            all_values = list(set(all_values))

            for item in all_values:
                if item not in json_data.keys():
                    json_data[item] = translate_using_google(to_lang=translation_languages[0], translate_str=item)  # TODO: check for API rate limit

            # write to file
            json_object = json.dumps(json_data, indent=2)
            with open(JSON_FILE, "w") as outfile:
                outfile.write(json_object)

            print("Done! Fetched strings from model and saved translation")

        def update_model_translation_columns():
            """
                Read existing .json file for key:value pairs
                Loop through all translator registered models to see if any row's translation field values are empty
                Update respective rows with language translation
            """

            json_data = {}
            with open(JSON_FILE, "r") as outfile:
                json_data = json.load(outfile)

            for key, value in json_data.items():

                for model in translator.get_registered_models():

                    translation_languages = get_translation_langauges()
                    field_names = translator.get_options_for_model(model).get_field_names()

                    filter_params = {}
                    for name in field_names:
                        k = '{}__icontains'.format(name)
                        filter_params[k] = key

                    filter_expression = Q()
                    for item in filter_params:
                        filter_expression |= Q(**{item: filter_params[item]})

                    for model_object in model.objects.filter(filter_expression):
                        for name in field_names:
                            for lang_code in translation_languages:
                                translation_field_name = name + '_' + lang_code
                                if hasattr(model_object, translation_field_name):
                                    if getattr(model_object, name) == key:
                                        setattr(model_object, translation_field_name, value)

                        model_object.save()

            print("Done! Saved translations to database model")

        # parse commands
        if options['generate']:
            generate_translation_strings_file_from_model()

        if options['update']:
            update_model_translation_columns()

        if options['all']:
            generate_translation_strings_file_from_model()
            update_model_translation_columns()
