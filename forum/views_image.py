import os
import mimetypes
from django.http import HttpResponse, Http404
from django.conf import settings
from django.shortcuts import get_object_or_404
from .models_image_mapping import ImageMapping

def serve_anonymous_image(request, clean_filename):
    """
    Serve images using their clean, anonymous filenames
    """
    try:
        # Find the original filename from the clean filename
        mapping = get_object_or_404(ImageMapping, clean_filename=clean_filename)
        original_filename = mapping.original_filename
        
        # Construct the full file path
        file_path = os.path.join(settings.MEDIA_ROOT, 'mdeditor', original_filename)
        
        if not os.path.exists(file_path):
            raise Http404("Image not found")
        
        # Get the MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            mime_type = 'application/octet-stream'
        
        # Serve the file
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type=mime_type)
            response['Content-Disposition'] = f'inline; filename="{clean_filename}"'
            return response
            
    except ImageMapping.DoesNotExist:
        raise Http404("Image mapping not found")
    except Exception as e:
        raise Http404(f"Error serving image: {str(e)}")
