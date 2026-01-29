from django.db.models import Q
from .models import Message

def unread_messages(request):
    if request.user.is_authenticated:
        # Tìm tin nhắn chưa đọc:
        # 1. Thuộc cuộc hội thoại có user1 hoặc user2 là mình
        # 2. Mình không phải người gửi (sender != mình)
        # 3. is_read là False
        count = Message.objects.filter(
            Q(conversation__user1=request.user) | Q(conversation__user2=request.user),
            is_read=False
        ).exclude(sender=request.user).count()
        
        # Debug log
        print(f"Unread count for {request.user.username}: {count}")
        
        return {'unread_messages_count': count}
    return {'unread_messages_count': 0}