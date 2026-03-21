from django import template
from allauth.socialaccount.models import SocialApp

register = template.Library()

@register.simple_tag
def google_login_available():
    """Check if Google OAuth2 is properly configured"""
    try:
        SocialApp.objects.get(provider='google')
        return True
    except SocialApp.DoesNotExist:
        return False
