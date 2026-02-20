"""Markdown rendering with sanitization for AI output."""

from __future__ import annotations

from typing import Iterable

import bleach
import markdown
from markupsafe import Markup

# Allow rich formatting while blocking unsafe HTML.
ALLOWED_TAGS: Iterable[str] = (
    "p",
    "pre",
    "code",
    "blockquote",
    "hr",
    "br",
    "ul",
    "ol",
    "li",
    "strong",
    "em",
    "b",
    "i",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "a",
)

ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "target", "rel"],
    "th": ["colspan", "rowspan"],
    "td": ["colspan", "rowspan"],
}


def render_markdown(text: str) -> Markup:
    """Convert markdown to sanitized HTML marked safe for templates."""
    if not text:
        return Markup("")

    html = markdown.markdown(
        text,
        extensions=["fenced_code", "tables", "sane_lists", "smarty"],
        output_format="html5",
    )

    cleaned = bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True)
    linked = bleach.linkify(cleaned, skip_tags=["code", "pre"], parse_email=False)
    return Markup(linked)
