from django import template
from django.utils.html import format_html
from django.utils.translation import gettext
from django.forms import CheckboxInput, CheckboxSelectMultiple, RadioSelect, Select, SelectMultiple

from ..permissions import request_has_perm

register = template.Library()


@register.simple_tag(takes_context=True)
def org_perm(context, perm: str) -> bool:
    request = context.get("request")
    return request is not None and request_has_perm(request, perm)


@register.filter
def mask_email(value: str) -> str:
    """Masque une adresse pour les rôles sans accès aux données personnelles."""
    if not value or "@" not in value:
        return "•••" if value else ""
    local, _, domain = value.partition("@")
    return f"{local[:1]}•••@{domain}"


@register.filter
def mask_text(value: str) -> str:
    return "•••" if value else ""


@register.filter
def widget_kind(bound_field) -> str:
    widget = bound_field.field.widget
    if isinstance(widget, CheckboxSelectMultiple):
        return "checkbox-multiple"
    if isinstance(widget, RadioSelect):
        return "radio"
    if isinstance(widget, CheckboxInput):
        return "checkbox"
    if isinstance(widget, (Select, SelectMultiple)):
        return "select"
    return "input"


@register.simple_tag(takes_context=True)
def query_transform(context, **kwargs) -> str:
    """Conserve les paramètres de filtre en changeant de page."""
    query = context["request"].GET.copy()
    for key, value in kwargs.items():
        if value in (None, ""):
            query.pop(key, None)
        else:
            query[key] = value
    return query.urlencode()


def plain_decimal(value) -> str:
    """Décimal lisible, sans zéros inutiles ni notation scientifique (10 et non 1E+1)."""
    from decimal import Decimal, InvalidOperation

    if value is None or value == "":
        return ""
    try:
        number = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return str(value)
    text = format(number, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


register.filter("plain_decimal", plain_decimal)


@register.filter
def decimal_display(value) -> str:
    """Décimal pour l'affichage, avec le séparateur de la langue active (0,35 en français)."""
    from django.utils.formats import get_format

    text = plain_decimal(value)
    return text.replace(".", get_format("DECIMAL_SEPARATOR")) if text else text


@register.filter
def or_absent(value, label=None):
    """Valeur, ou mention d'absence en texte atténué : une absence ne doit pas ressembler à une donnée."""
    if value not in (None, ""):
        return value
    return format_html('<span class="sc-absent">{}</span>', label or gettext("Not provided"))
