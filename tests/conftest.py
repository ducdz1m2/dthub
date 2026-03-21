import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dthub.settings")


def pytest_configure(config):
    django.setup()
