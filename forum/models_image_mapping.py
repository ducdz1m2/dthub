from django.db import models
import uuid
import os

class ImageMapping(models.Model):
    """Model to map original image filenames to clean, anonymous filenames"""
    original_filename = models.CharField(max_length=500)
    clean_filename = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'forum_image_mapping'
        verbose_name = 'Image Mapping'
        verbose_name_plural = 'Image Mappings'
    
    @classmethod
    def get_or_create_mapping(cls, original_path):
        """Get existing mapping or create new one"""
        filename = os.path.basename(original_path)
        
        # Try to find existing mapping
        try:
            mapping = cls.objects.get(original_filename=filename)
            return mapping.clean_filename
        except cls.DoesNotExist:
            # Create new mapping
            name, ext = os.path.splitext(filename)
            clean_filename = f"img_{uuid.uuid4().hex[:12]}{ext}"
            
            mapping = cls.objects.create(
                original_filename=filename,
                clean_filename=clean_filename
            )
            return clean_filename
