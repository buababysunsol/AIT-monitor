from django import template

from network_monitor.utils import timedelta_human

register = template.Library()


@register.filter
def diff(d1, d2):
    if d2 is None or d1 is None:
        return 'N/A'
    return timedelta_human(d1 - d2)
