"""
Database Helpers - Các hàm tiện ích cho thao tác database
"""

from asgiref.sync import sync_to_async


@sync_to_async
def get_chat_history_async(session_id, limit=10, user_id=None):
    """Lấy lịch sử chat từ Database (Async)"""
    from ..models import ChatSession, ChatMessage
    try:
        session, created = ChatSession.objects.get_or_create(session_id=session_id)
        if user_id and not session.user_id:
            # Attach authenticated user to session for proper ownership & clearing.
            session.user_id = user_id
            session.save(update_fields=["user"])
        messages = ChatMessage.objects.filter(session=session).order_by('-timestamp')[:limit]

        formatted_history = []
        for msg in reversed(messages):
            formatted_history.append({"role": "user", "content": msg.query})
            formatted_history.append({"role": "assistant", "content": msg.response})
        return formatted_history
    except Exception as e:
        print(f"Error getting history: {e}")
        return []


@sync_to_async
def save_chat_message_async(session_id, query, response, tool_used, response_time=0, user_id=None):
    """Lưu tin nhắn vào Database (Async)"""
    from ..models import ChatSession, ChatMessage
    try:
        session, created = ChatSession.objects.get_or_create(session_id=session_id)
        if user_id and not session.user_id:
            session.user_id = user_id
            session.save(update_fields=["user"])
        ChatMessage.objects.create(
            session=session,
            query=query,
            response=response,
            tool_used=tool_used,
            response_time=response_time
        )
        print(f"Successfully saved message for session {session_id}")
    except Exception as e:
        print(f"Error saving message: {e}")


def get_chat_history_sync(session_id, limit=5, user_id=None):
    """Lấy lịch sử chat từ Database (Sync)"""
    from ..models import ChatSession, ChatMessage
    try:
        session, created = ChatSession.objects.get_or_create(session_id=session_id)
        if user_id and not session.user_id:
            session.user_id = user_id
            session.save(update_fields=["user"])
        messages = ChatMessage.objects.filter(session=session).order_by('-timestamp')[:limit]

        formatted_history = []
        for msg in reversed(messages):
            formatted_history.append({"role": "user", "content": msg.query})
            formatted_history.append({"role": "assistant", "content": msg.response})
        return formatted_history
    except Exception as e:
        print(f"Error getting history: {e}")
        return []


def save_chat_message_sync(session_id, query, response, tool_used, response_time=0, user_id=None):
    """Lưu tin nhắn vào Database (Sync)"""
    from ..models import ChatSession, ChatMessage
    try:
        session, created = ChatSession.objects.get_or_create(session_id=session_id)
        if user_id and not session.user_id:
            session.user_id = user_id
            session.save(update_fields=["user"])
        ChatMessage.objects.create(
            session=session,
            query=query,
            response=response,
            tool_used=tool_used,
            response_time=response_time
        )
    except Exception as e:
        print(f"Error saving message: {e}")
