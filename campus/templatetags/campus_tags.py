from django import template
register = template.Library()

@register.filter
def get_item(value, key):
    if value is None:
        return None
    try:
        return value.get(key)
    except (AttributeError, TypeError):
        try:
            return value[key]
        except (KeyError, IndexError, TypeError):
            return None
