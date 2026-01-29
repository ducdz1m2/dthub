import os
import django
from django.conf import settings

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dthub.settings')
django.setup()

from django.contrib.auth import get_user_model
from forum.models import Post, Tag, ForumCategory
from forum.utils import render_markdown
import uuid

User = get_user_model()

# Get or create a test user
user, created = User.objects.get_or_create(
    username='testuser',
    defaults={'email': 'test@example.com'}
)

# Get first category and some tags
category = ForumCategory.objects.first()
tags = Tag.objects.all()[:3]

# Create a test post
post = Post.objects.create(
    id=uuid.uuid4(),
    author=user,
    title='ESP32 Tutorial: Getting Started with MicroPython',
    content='''# ESP32 MicroPython Tutorial

## Introduction
This tutorial will help you get started with ESP32 development using MicroPython.

## What You'll Need
- ESP32 Development Board
- USB Cable
- Computer

## Installation Steps

### 1. Install MicroPython
```python
print("Hello, ESP32!")
```

### 2. Connect to WiFi
```python
import network
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect("SSID", "password")
```

## Next Steps
- Try blinking an LED
- Read sensor data
- Connect to IoT platforms

Happy coding!''',
    post_type='wiki',
    category=category
)

# Add tags
post.tags.set(tags)

# Render HTML
post.content_html = render_markdown(post.content)
post.save()

print(f'Created post: {post.title}')
print(f'URL: /forum/post/{post.slug}/')
