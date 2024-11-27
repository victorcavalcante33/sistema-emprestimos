from django import template

register = template.Library()

@register.simple_tag
def toggle_order(current_order, asc_value, desc_value):
    if current_order == asc_value:
        return desc_value
    else:
        return asc_value
