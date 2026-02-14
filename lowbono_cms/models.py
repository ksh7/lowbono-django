from django.db import models
from ckeditor.fields import RichTextField
from djangocms_text_ckeditor.fields import HTMLField
from cms.models import CMSPlugin


class CMSPlainText(CMSPlugin):
    text = models.TextField()

    def __str__(self):
        return self.text


class CMSRichText(CMSPlugin):
    content = RichTextField()

    def __str__(self):
        return self.content[:50] + " ..."


class CMSHTMLContent(CMSPlugin):
    content = HTMLField()

    def __str__(self):
        return self.content[:50] + " ..."


class DivElement(CMSPlugin):
    class_names = models.CharField(blank=True, null=True, max_length=255)

    def __str__(self):
        return self.class_names if self.class_names else ""


class CMSRichTextResourceCard(CMSPlugin):
    title = models.CharField(max_length=256)
    body = RichTextField()

    def __str__(self):
        return self.title


class CMSRichTextMemberCard(CMSPlugin):
    photo = models.ImageField(upload_to='headshots')
    name = models.CharField(max_length=256)
    description = RichTextField()

    def __str__(self):
        return self.name


class CMSSidebarImgDescBtnCard(CMSPlugin):
    photo = models.ImageField(upload_to='cms_images')
    description = HTMLField()
    button_text = models.CharField(max_length=256)
    button_url = models.CharField(max_length=256)

    def __str__(self):
        return self.description[:20] + " ..."


class CMSAccordionBaseCard(CMSPlugin):
    name = models.CharField(max_length=256)

    def __str__(self):
        return self.name


class CMSAccordionItem(CMSPlugin):
    accordion = models.ForeignKey(CMSAccordionBaseCard, on_delete=models.CASCADE)
    heading = models.CharField(max_length=256)
    description = HTMLField()

    def __str__(self):
        return self.heading


class CMSThemeTwoImgsCard(CMSPlugin):
    photo_left = models.ImageField(upload_to='cms_images')
    photo_right = models.ImageField(upload_to='cms_images')


class CMSThemeIconBlockCard(CMSPlugin):
    svg_code = HTMLField()
    title = models.CharField(max_length=256)
    description = models.TextField()


class CMSThemeBackgroundColorImageBtnCard(CMSPlugin):
    name = models.CharField(max_length=128)
    title = models.CharField(max_length=128)
    description = models.TextField()
    bg_color = models.CharField(max_length=32, default='bg-primary', choices=[("bg-primary", "Primary Color"), ("bg-secondary", "Secondary Color"), ("bg-success", "Success Color"), ("bg-danger", "Danger Color"), ("bg-warning", "Warning Color"), ("bg-info", "Info Color")])
    overlay_image = models.ImageField(upload_to='cms_images', blank=True)
    btn_href = models.URLField(max_length=256, blank=True)
    btn_description = models.CharField(max_length=64, blank=True)

    def __str__(self):
        return self.name


class CMSThemeQuoteCard(CMSPlugin):
    title = models.CharField(max_length=128, blank=True, null=True)
    brand_image = models.ImageField(upload_to='cms_images', blank=True)
    quote = models.TextField()
    person_image = models.ImageField(upload_to='cms_images', blank=True)
    person_name = models.CharField(max_length=128)
    person_designation = models.CharField(max_length=128, blank=True, null=True)

    def __str__(self):
        return self.quote[:20] + " ..."


class CMSThemeCTACard(CMSPlugin):
    description = models.TextField()
    btn_color = models.CharField(max_length=32, default='primary', choices=[("primary", "Primary"), ("secondary", "Secondary"), ("success", "Success"), ("danger", "Danger"), ("warning", "Warning"), ("info", "Info")])
    btn_href = models.URLField(max_length=256, blank=True)
    btn_name = models.CharField(max_length=64, blank=True)


class CMSThemeSupporterBoxBaseCard(CMSPlugin):
    name = models.CharField(max_length=256)

    def __str__(self):
        return self.name


class CMSThemeSupporterBoxItem(CMSPlugin):
    support_box = models.ForeignKey(CMSThemeSupporterBoxBaseCard, on_delete=models.CASCADE)
    brand_name = models.ImageField(upload_to='cms_images')
    brand_image = models.ImageField(upload_to='cms_images')


class CMSThemeStatsCard(CMSPlugin):
    stats = models.CharField(max_length=32)
    description = models.CharField(max_length=128)
