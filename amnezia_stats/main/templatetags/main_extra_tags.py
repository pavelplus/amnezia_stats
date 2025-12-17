from django import template

from main.utils import bytes_to_hrs as _bytes_to_hrs

register = template.Library()


@register.filter
def bytes_to_hrs(bytes):
    return _bytes_to_hrs(bytes)


@register.filter
def bytes_avg(bytes, seconds):
    return round(bytes/seconds) if seconds else 0


@register.filter
def add_class(field, css_class):
    return field.as_widget(attrs={"class": css_class})