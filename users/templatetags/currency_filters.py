from django import template

register = template.Library()


@register.filter
def cop_format(value):
    """
    Format a number as Colombian Pesos (COP).
    Example: 100000 -> $100.000
    """
    try:
        num = int(value)
        return f"${num:,}"
    except (ValueError, TypeError):
        return f"${value}"


@register.filter
def currency(value):
    """
    Format a number as Colombian Pesos (COP).
    Example: 100000 -> $100,000 COP
    """
    try:
        num = int(value)
        return f"${num:,} COP"
    except (ValueError, TypeError):
        return f"${value} COP"
