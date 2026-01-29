#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dthub.settings')
django.setup()

from forum.models import Category

print('Categories count:', Category.objects.count())
for cat in Category.objects.all():
    print(f'- {cat.name} ({cat.slug})')
