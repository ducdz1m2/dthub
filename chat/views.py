from django.shortcuts import get_object_or_404, render
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from .models import Conversation, Message
from django.db.models import Q
from django.http import JsonResponse

@login_required
def load_more_messages(request, conversation_id):
    offset = int(request.GET.get('offset', 0))
    limit = 20
    
    messages = Message.objects.filter(conversation_id=conversation_id).order_by('-timestamp')[offset:offset+limit]
    
    data = []
    for msg in messages:
        data.append({
            'sender_id': msg.sender.id,
            'text': msg.text,
            'timestamp': msg.timestamp.strftime("%H:%M - %d/%m/%Y"),
        })
    
    return JsonResponse({'messages': data, 'has_more': len(data) == limit})

User = get_user_model()


@login_required
def chat_home(request):
    admin_groups = ["ProductOrderManager", "ContentFeedbackManager", "AIArchitect"]
    is_admin = request.user.groups.filter(name__in=admin_groups).exists() or request.user.is_superuser

    if is_admin:
        users = User.objects.exclude(id=request.user.id)
    else:
        users = User.objects.filter(
            Q(groups__name__in=admin_groups) | Q(is_superuser=True)
        ).distinct()

 
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
    other_user = get_object_or_404(User, id=other_id)
    user1, user2 = sorted([request.user.id, other_id])
    conversation, created = Conversation.objects.get_or_create(
        user1_id=user1, user2_id=user2
    )

  
    Message.objects.filter(conversation=conversation, is_read=False).exclude(sender=request.user).update(is_read=True)

  
    messages = conversation.messages.order_by('-timestamp')[:20][::-1]

    return render(request, 'chat/room.html', {
        'other_user': other_user,
        'chat_messages': messages,
        'conversation_id': conversation.id 
    })