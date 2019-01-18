from django import template

register = template.Library()


@register.simple_tag
def usage_to_percent(value, max_value, point):
    try:
        value = float(value)
        max_value = float(max_value)
        percent = value / max_value * 100
        return "{percent:.{point:}f}".format(percent=percent, point=point)
    except ValueError:
        0
    return 0
