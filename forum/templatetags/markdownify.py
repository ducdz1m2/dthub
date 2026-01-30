import markdown
import re
import uuid
import os
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def markdownify(text):
    """
    Convert markdown to HTML with image anonymization
    """
    if not text:
        return text
    
    # Fix image paths first
    text = fix_image_paths(text)
    
    # Convert markdown to HTML
    html = markdown.markdown(text, extensions=['extra', 'codehilite', 'toc'])
    
    return mark_safe(html)

def fix_image_paths(text):
    """
    Fix image paths by converting backslashes to forward slashes
    and generating clean, anonymous filenames
    """
    # Pattern to match markdown image syntax: ![alt](path "title")
    pattern = r'!\[([^\]]*)\]\(([^)]+?)(?:\s+"([^"]*)")?\)'
    
    def replace_image(match):
        alt_text = match.group(1)
        original_path = match.group(2)
        title = match.group(3) if match.group(3) else ""
        
        # Convert backslashes to forward slashes
        clean_path = original_path.replace('\\', '/')
        
        # Generate a clean filename if it's a media/mdeditor path
        if '/media/mdeditor/' in clean_path or clean_path.startswith('/media/mdeditor/'):
            clean_path = generate_clean_image_path(clean_path)
        
        # Reconstruct the image markdown with title if it existed
        if title:
            return f'![{alt_text}]({clean_path} "{title}")'
        else:
            return f'![{alt_text}]({clean_path})'
    
    return re.sub(pattern, replace_image, text)

def generate_clean_image_path(original_path):
    """
    Generate a clean, anonymous path for images using forum URL
    """
    try:
        # Import here to avoid circular imports
        from forum.models_image_mapping import ImageMapping
        
        # Get or create mapping
        clean_filename = ImageMapping.get_or_create_mapping(original_path)
        
        # Return the anonymous URL path
        return f"/forum/image/{clean_filename}"
        
    except Exception as e:
        # Fallback to simple UUID generation if anything goes wrong
        filename = os.path.basename(original_path)
        name, ext = os.path.splitext(filename)
        clean_filename = f"img_{uuid.uuid4().hex[:8]}{ext}"
        
        return f"/forum/image/{clean_filename}"
