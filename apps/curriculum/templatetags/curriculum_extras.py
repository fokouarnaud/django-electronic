import markdown
from django import template
from django.utils.safestring import mark_safe
from markdown.extensions import Extension

register = template.Library()


class _NoRawHTML(Extension):
    """Treat raw HTML in the source as plain text so it gets escaped."""

    def extendMarkdown(self, md):
        md.preprocessors.deregister("html_block")
        md.inlinePatterns.deregister("html")


@register.filter
def render_markdown(text):
    if not text:
        return ""
    # Fresh instance per call: markdown.Markdown objects are not thread-safe.
    extensions = [_NoRawHTML(), "fenced_code", "tables", "sane_lists"]
    # Safe: _NoRawHTML disables raw HTML, so Markdown only emits its own tags and escapes the rest.
    return mark_safe(markdown.markdown(text, extensions=extensions))  # noqa: S308
