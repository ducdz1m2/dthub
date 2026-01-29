import os
import django
from django.conf import settings

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dthub.settings')
django.setup()

from django.contrib.auth import get_user_model
from forum.models import Post, Tag, ForumCategory

User = get_user_model()

# Get or create a test user
user, created = User.objects.get_or_create(
    username='testuser',
    defaults={'email': 'test@example.com'}
)

# Get first category
category = ForumCategory.objects.first()

# Create a simple test post without UUID
try:
    post = Post.objects.create(
        author=user,
        title='Test Post - ESP32 Basic Tutorial',
        content='''# ESP32 Tutorial

This is a simple test post for the forum.

## Code Example
```python
print("Hello ESP32!")
```

## Features
- WiFi connectivity
- Bluetooth support
- Low power consumption''',
        post_type='discussion',
        category=category
    )
    
    print(f'Created post: {post.title}')
    print(f'Slug: {post.slug}')
    print(f'URL: /forum/post/{post.slug}/')
    
except Exception as e:
    print(f'Error: {e}')
    print('Creating post without category...')
    
    post = Post.objects.create(
        author=user,
        title='Simple Test Post',
        content='This is a simple test post for the forum.',
        post_type='discussion'
    )
    
    print(f'Created simple post: {post.title}')
    print(f'Slug: {post.slug}')
