from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from .models import CMSPlainText, CMSRichText, CMSHTMLContent, CMSRichTextResourceCard, CMSRichTextMemberCard, CMSSidebarImgDescBtnCard, CMSAccordionBaseCard, CMSAccordionItem, DivElement, \
                    CMSThemeTwoImgsCard, CMSThemeIconBlockCard, CMSThemeBackgroundColorImageBtnCard, CMSThemeQuoteCard, CMSThemeCTACard, CMSThemeSupporterBoxBaseCard, CMSThemeSupporterBoxItem, \
                    CMSThemeStatsCard
from django.utils.translation import gettext as _


@plugin_pool.register_plugin
class CMSPlainTextPlugin(CMSPluginBase):
    model = CMSPlainText
    name = _("Plain Text")
    render_template = "lowbono_cms/plugins/plain_text.html"

    def render(self, context, instance, placeholder):
        context.update({'text': instance.text })
        return context


@plugin_pool.register_plugin
class CMSRichTextPlugin(CMSPluginBase):
    model = CMSRichText
    name = _("Rich Text")
    render_template = "lowbono_cms/plugins/rich_text.html"

    def render(self, context, instance, placeholder):
        context.update({'content': instance.content })
        return context


@plugin_pool.register_plugin
class CMSHTMLContentPlugin(CMSPluginBase):
    model = CMSHTMLContent
    name = _("HTML Code")
    render_template = "lowbono_cms/plugins/html_content.html"

    def render(self, context, instance, placeholder):
        context.update({'content': instance.content })
        return context


@plugin_pool.register_plugin
class CMSRichTextResourceCardPlugin(CMSPluginBase):
    model = CMSRichTextResourceCard
    name = _("Resource Card")
    render_template = "lowbono_cms/plugins/resource_card.html"

    def render(self, context, instance, placeholder):
        context.update({'instance': instance })
        return context


@plugin_pool.register_plugin
class CMSRichTextMemberCardPlugin(CMSPluginBase):
    model = CMSRichTextMemberCard
    name = _("Member Card")
    render_template = "lowbono_cms/plugins/member_card.html"

    def render(self, context, instance, placeholder):
        context.update({'instance': instance })
        return context


@plugin_pool.register_plugin
class CMSSidebarImgDescBtnCardPlugin(CMSPluginBase):
    model = CMSSidebarImgDescBtnCard
    name = _("Sidebar Card: Image Description Button")
    render_template = "lowbono_cms/plugins/sidebar_img_desc_btn_card.html"

    def render(self, context, instance, placeholder):
        context.update({'instance': instance })
        return context


@plugin_pool.register_plugin
class CMSAccordionBasePlugin(CMSPluginBase):
    model = CMSAccordionBaseCard
    render_template = "lowbono_cms/plugins/accordion_base.html"
    name = _("Accordion Base")
    allow_children = True
    child_classes = ['CMSAccordionItemPlugin']

    def render(self, context, instance, placeholder):
        context.update({'instance': instance})
        return context


@plugin_pool.register_plugin
class CMSAccordionItemPlugin(CMSPluginBase):
    model = CMSAccordionItem
    render_template = "lowbono_cms/plugins/accordion_item.html"
    name = _("Accordion Item")
    parent_classes = ['CMSAccordionBasePlugin']
    require_parent = True

    def render(self, context, instance, placeholder):
        context.update({'instance': instance})
        return context


@plugin_pool.register_plugin
class DivElementPlugin(CMSPluginBase):
    model = DivElement
    render_template = "lowbono_cms/plugins/div_element.html"
    name = _("Div Element")
    allow_children = True

    def render(self, context, instance, placeholder):
        context.update({'instance': instance})
        return context


@plugin_pool.register_plugin
class CMSNewsArticlesPlugin(CMSPluginBase):
    render_template = "lowbono_cms/plugins/all_news_articles.html"
    name = _("All News Articles Component")

    def render(self, context, instance, placeholder):
        from lowbono_app.models import NewsArticles
        news_articles = NewsArticles.objects.filter(status='published')
        context.update({'news_articles': news_articles})
        return context


@plugin_pool.register_plugin
class CMSThemeTwoImgsCardPlugin(CMSPluginBase):
    model = CMSThemeTwoImgsCard
    name = _("Theme: Two Images Card")
    render_template = "lowbono_cms/plugins/theme_two_images.html"

    def render(self, context, instance, placeholder):
        context.update({'instance': instance })
        return context


@plugin_pool.register_plugin
class CMSThemeIconBlockCardPlugin(CMSPluginBase):
    model = CMSThemeIconBlockCard
    name = _("Theme: Icon Block Card")
    render_template = "lowbono_cms/plugins/icon_block_card.html"

    def render(self, context, instance, placeholder):
        context.update({'instance': instance })
        return context


@plugin_pool.register_plugin
class CMSThemeBackgroundColorImageBtnCardPlugin(CMSPluginBase):
    model = CMSThemeBackgroundColorImageBtnCard
    name = _("Theme: Card with Background Color, Image & Button")
    render_template = "lowbono_cms/plugins/background_color_image_btn_card.html"

    def render(self, context, instance, placeholder):
        context.update({'instance': instance })
        return context


@plugin_pool.register_plugin
class CMSThemeQuote1CardPlugin(CMSPluginBase):
    model = CMSThemeQuoteCard
    name = _("Theme: Quote Type 1 Card")
    render_template = "lowbono_cms/plugins/quote_type_1_card.html"

    def render(self, context, instance, placeholder):
        context.update({'instance': instance })
        return context

@plugin_pool.register_plugin
class CMSThemeQuote2CardPlugin(CMSPluginBase):
    model = CMSThemeQuoteCard
    name = _("Theme: Quote Type 2 Card")
    render_template = "lowbono_cms/plugins/quote_type_2_card.html"

    def render(self, context, instance, placeholder):
        context.update({'instance': instance })
        return context


@plugin_pool.register_plugin
class CMSThemeQuote3CardPlugin(CMSPluginBase):
    model = CMSThemeQuoteCard
    name = _("Theme: Quote Type 3 Card")
    render_template = "lowbono_cms/plugins/quote_type_3_card.html"

    def render(self, context, instance, placeholder):
        context.update({'instance': instance })
        return context


@plugin_pool.register_plugin
class CMSThemeQuote4CardPlugin(CMSPluginBase):
    model = CMSThemeQuoteCard
    name = _("Theme: Quote Type 4 Card")
    render_template = "lowbono_cms/plugins/quote_type_4_card.html"

    def render(self, context, instance, placeholder):
        context.update({'instance': instance })
        return context

@plugin_pool.register_plugin
class CMSThemeCTACardPlugin(CMSPluginBase):
    model = CMSThemeCTACard
    name = _("Theme: Call to Action Card")
    render_template = "lowbono_cms/plugins/cta_card.html"

    def render(self, context, instance, placeholder):
        context.update({'instance': instance })
        return context


@plugin_pool.register_plugin
class CMSThemeSupporterBoxBasePlugin(CMSPluginBase):
    model = CMSThemeSupporterBoxBaseCard
    render_template = "lowbono_cms/plugins/supporter_box_base.html"
    name = _("Theme: Supporter Box Base")
    allow_children = True
    child_classes = ['CMSThemeSupporterBoxItemPlugin']

    def render(self, context, instance, placeholder):
        context.update({'instance': instance})
        return context


@plugin_pool.register_plugin
class CMSThemeSupporterBoxItemPlugin(CMSPluginBase):
    model = CMSThemeSupporterBoxItem
    render_template = "lowbono_cms/plugins/supporter_box_item.html"
    name = _("Theme: Supporter Box Item")
    parent_classes = ['CMSThemeSupporterBoxBasePlugin']
    require_parent = True

    def render(self, context, instance, placeholder):
        context.update({'instance': instance})
        return context


@plugin_pool.register_plugin
class CMSThemeStatsCardPlugin(CMSPluginBase):
    model = CMSThemeStatsCard
    name = _("Theme: Stats Card")
    render_template = "lowbono_cms/plugins/stats_card.html"

    def render(self, context, instance, placeholder):
        context.update({'instance': instance })
        return context
