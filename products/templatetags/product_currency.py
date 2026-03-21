from django import template

register = template.Library()

@register.filter
def vnd_currency(value):
    """
    Format number as Vietnamese currency with proper thousand separators
    Example: 1500000 -> 1.500.000
    """
    try:
        if value is None:
            return ''
        
        # Convert to integer if it's a decimal/float
        if isinstance(value, (float, str)):
            value = int(float(value))
        
        # Format with dots as thousand separators
        return f"{value:,}".replace(',', '.')
    except (ValueError, TypeError):
        return value

@register.filter
def vnd_price(value):
    """
    Format number as Vietnamese currency with ₫ symbol
    Example: 1500000 -> 1.500.000₫
    """
    try:
        if value is None:
            return 'Liên hệ báo giá'
        
        # Convert to integer if it's a decimal/float
        if isinstance(value, (float, str)):
            value = int(float(value))
        
        # Format with dots as thousand separators and add ₫ symbol
        return f"{value:,}".replace(',', '.') + '₫'
    except (ValueError, TypeError):
        return 'Liên hệ báo giá'
