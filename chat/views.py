from django.shortcuts import get_object_or_404, render
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from .models import Conversation, Message
from django.db.models import Q
from django.http import JsonResponse

User = get_user_model()


@login_required
def chat_home(request):
    """Trang chủ danh sách chat"""
    admin_groups = ["ProductOrderManager", "ContentFeedbackManager", "AIArchitect"]
    is_admin = request.user.groups.filter(name__in=admin_groups).exists() or request.user.is_superuser

    if is_admin:
        users = User.objects.exclude(id=request.user.id)
    else:
        users = User.objects.filter(
            Q(groups__name__in=admin_groups) | Q(is_superuser=True)
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

    return render(request, 'chat/room.html', {
        'other_user': other_user,
        'chat_messages': messages,
        'conversation_id': conversation.id,
        'new_message_start_index': new_message_start_index
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
