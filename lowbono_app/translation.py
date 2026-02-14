from modeltranslation.translator import translator, TranslationOptions
from . import models


class PracticeAreaCategoryTranslationOptions(TranslationOptions):
    fields = ('title', 'definition')

class PracticeAreaTranslationOptions(TranslationOptions):
    fields = ('title', 'definition')

translator.register(models.PracticeAreaCategory, PracticeAreaCategoryTranslationOptions)
translator.register(models.PracticeArea, PracticeAreaTranslationOptions)
