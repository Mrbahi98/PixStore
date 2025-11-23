from django import template
from django.conf import settings

register = template.Library()

@register.filter
def usd(value):
    try:
        return round(float(value) / settings.DZD_PER_USD, 2)
    except:
        return "0.00"
