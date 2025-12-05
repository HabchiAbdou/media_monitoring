from django import template

from monitoring.translations import TRANSLATIONS_FR

register = template.Library()


@register.filter(name="t")
def translate(key: object) -> str:
    """
    Simple French translation lookup. Falls back to the provided key if missing.
    Default locale: fr.
    """
    if key is None:
        return ""
    text = str(key)
    return TRANSLATIONS_FR.get(text, text)


@register.simple_tag(name="t")
def translate_tag(key: object, **kwargs) -> str:
    """
    Template tag version supporting string formatting, e.g.:
        {% t "Welcome back! You have {count} new urgent alerts that require attention." count=5 %}
    """
    text = translate(key)
    try:
        return text.format(**kwargs)
    except Exception:
        return text
