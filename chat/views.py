from django.shortcuts import get_object_or_404, render
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import Conversation, Message
from django.db.models import Q

User = get_user_model()


@login_required
def chat_home(request):
    """Trang chủ danh sách chat"""
    # Chỉ admin mới có thể xem tất cả users
    is_admin = request.user.is_superuser

    if is_admin:
        users = User.objects.exclude(id=request.user.id)
    else:
        # Khách hàng chỉ chat với admin
        users = User.objects.filter(
            is_superuser=True
        ).distinct()

    # Tính số tin nhắn chưa đọc cho mỗi user
    for person in users:
        user1, user2 = sorted([request.user.id, person.id])
        person.unread_count = Message.objects.filter(
            conversation__user1_id=user1,
            conversation__user2_id=user2,
            sender=person,
            is_read=False
        ).count()
    
    return render(request, 'chat/home.html', {'users': users})


@login_required
def chat_room(request, other_id):
    """Phòng chat"""
    other_user = get_object_or_404(User, id=other_id)
    user1, user2 = sorted([request.user.id, other_id])
    conversation, created = Conversation.objects.get_or_create(
        user1_id=user1, user2_id=user2
    )

    # Lấy 20 tin nhắn gần nhất khi mới vào phòng
    messages = conversation.messages.order_by('-timestamp')[:20][::-1]
    
    # Tìm tin nhắn cuối cùng từ người khác mà user CHƯA đọc
    unread_messages = Message.objects.filter(
        conversation=conversation,
        sender=other_user,
        is_read=False
    ).order_by('timestamp')
    
    # Đánh dấu vị trí bắt đầu tin nhắn mới
    new_message_start_index = None
    if unread_messages.exists():
        # Tìm tin nhắn chưa đọc đầu tiên trong danh sách hiển thị
        first_unread = unread_messages.first()
        for i, msg in enumerate(messages):
            if msg.id == first_unread.id:
                new_message_start_index = i
                break
    
    # Đánh dấu tin nhắn đã đọc khi vào phòng (sau khi đã xác định tin nhắn mới)
    Message.objects.filter(
        conversation=conversation, 
        is_read=False
    ).exclude(sender=request.user).update(is_read=True)

    consultation_info = request.session.get('consultation_product_info', '')
    print(f"DEBUG: Retrieved consultation info: {consultation_info}")  # Debug print

    return render(request, 'chat/room.html', {
        'other_user': other_user,
        'chat_messages': messages,
        'conversation_id': conversation.id,
        'new_message_start_index': new_message_start_index,
        'consultation_product_info': consultation_info
    })


@login_required
def load_more_messages(request, conversation_id):
    """Tải thêm tin nhắn cũ"""
    try:
        offset = int(request.GET.get('offset', 0))
        limit = 20
        
        # Kiểm tra conversation tồn tại
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        # Kiểm tra user có quyền xem conversation này không
        if conversation.user1_id != request.user.id and conversation.user2_id != request.user.id:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        
        messages = Message.objects.filter(
            conversation_id=conversation_id
        ).order_by('-timestamp')[offset:offset+limit]
        
        data = []
        for msg in messages:
            data.append({
                'sender_id': msg.sender.id,
                'text': msg.text,
                'timestamp': msg.timestamp.strftime("%H:%M - %d/%m/%Y"),
            })
        
        return JsonResponse({'messages': data, 'has_more': len(data) == limit})
    
    except ValueError:
        return JsonResponse({'error': 'Invalid offset parameter'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@login_required
def upload_chat_image(request):
    """Upload ảnh chat và trả về URL"""
    if request.method == 'POST':
        try:
            image_file = request.FILES.get('image')
            if not image_file:
                return JsonResponse({'error': 'No image file'}, status=400)
            
            # Validate file size (2MB max)
            if image_file.size > 2 * 1024 * 1024:
                return JsonResponse({'error': 'File too large. Maximum size is 2MB.'}, status=400)
            
            # Validate file type
            if not image_file.content_type.startswith('image/'):
                return JsonResponse({'error': 'Invalid file type. Please upload an image.'}, status=400)
            
            # Generate unique filename
            import uuid
            from django.utils import timezone
            ext = image_file.name.split('.')[-1]
            filename = f"chat_{timezone.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"
            
            # Save to media/chat_images/
            import os
            from django.conf import settings
            chat_images_dir = os.path.join(settings.MEDIA_ROOT, 'chat_images')
            os.makedirs(chat_images_dir, exist_ok=True)
            
            filepath = os.path.join(chat_images_dir, filename)
            with open(filepath, 'wb') as f:
                for chunk in image_file.chunks():
                    f.write(chunk)
            
            # Return URL
            image_url = f"/media/chat_images/{filename}"
            return JsonResponse({'success': True, 'image_url': image_url})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
@login_required
def mark_read(request, other_id):
    """Mark all messages as read when leaving chat room"""
    if request.method == 'POST':
        try:
            other_user = get_object_or_404(User, id=other_id)
            user1, user2 = sorted([request.user.id, other_user.id])
            conversation = get_object_or_404(Conversation, user1_id=user1, user2_id=user2)
            
            # Mark all unread messages from other user as read
            Message.objects.filter(
                conversation=conversation,
                sender=other_user,
                is_read=False
            ).update(is_read=True)
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
@login_required
def clear_consultation_session(request):
    """Xóa thông tin tư vấn sản phẩm khỏi session"""
    if request.method == 'POST':
        if 'consultation_product_info' in request.session:
            del request.session['consultation_product_info']
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Method not allowed'}, status=405)
