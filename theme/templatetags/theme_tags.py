from django import template
from django.conf import settings
from django.urls import translate_url
from django.utils.html import format_html_join

register = template.Library()


@register.simple_tag(takes_context=True)
def hreflang_links(context):
    """<link rel="alternate" hreflang=…> for every language of the current page,
    plus x-default (the default language), so search engines pair FR and EN."""
    request = context.get("request")
    if request is None:
        return ""
    current = request.get_full_path()

    def absolute(code):
        return request.build_absolute_uri(translate_url(current, code))

    links = [(code, absolute(code)) for code, _name in settings.LANGUAGES]
    links.append(("x-default", absolute(settings.LANGUAGE_CODE)))
    return format_html_join("\n", '<link rel="alternate" hreflang="{}" href="{}">', links)
