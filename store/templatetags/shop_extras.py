from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def money(value):
    """Format a number as Indian Rupees, e.g. 1299 -> ₹1,299.00"""
    try:
        return f'₹{Decimal(value):,.2f}'
    except Exception:
        return value
