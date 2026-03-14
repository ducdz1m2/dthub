"""
ESP32 Interaction API - Cung cấp cơ chế Hybrid Session cho thiết bị ngoại vi
"""

import json
import logging
import secrets
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
from .models import ESP32Device, ChatSession, ChatMessage

logger = logging.getLogger(__name__)

def authenticate_device(request):
    """Xác thực thiết bị qua Token trong Header hoặc Body"""
    auth_header = request.headers.get('Authorization', '')
    token = None
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
    else:
        try:
            data = json.loads(request.body)
            token = data.get('token')
        except:
            token = request.POST.get('token') or request.GET.get('token')

    if not token:
        return None, JsonResponse({'error': 'Yêu cầu Token xác thực (auth_token)'}, status=401)

    device = ESP32Device.objects.filter(auth_token=token, is_active=True).first()
    if not device:
        return None, JsonResponse({'error': 'Token không hợp lệ hoặc thiết bị đã bị khóa'}, status=401)
    
    # Cập nhật thời gian hoạt động cuối cùng
    device.last_seen = timezone.now()
    device.save(update_fields=['last_seen'])
    
    return device, None

@csrf_exempt
def esp32_session_handshake(request):
    """
    ESP32 gọi API này để lấy session_id mới hoặc kiểm tra session cũ.
    Cơ chế Hybrid Session: Session tồn tại trong 1 giờ.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Chỉ chấp nhận phương thức POST'}, status=405)

    device, error_response = authenticate_device(request)
    if error_response:
        return error_response

    # Kiểm tra xem thiết bị đã có session nào còn hạn không
    now = timezone.now()
    active_session = ChatSession.objects.filter(
        device=device,
        is_active=True,
        expires_at__gt=now
    ).order_by('-created_at').first()

    if active_session:
        # Nếu còn hạn, gia hạn thêm 30 phút (tối đa 2 giờ tổng cộng)
        active_session.expires_at = now + timedelta(minutes=60)
        active_session.save()
        return JsonResponse({
            'status': 'success',
            'session_id': active_session.session_id,
            'expires_at': active_session.expires_at.isoformat(),
            'message': 'Đã gia hạn session hiện tại'
        })

    # Nếu không có hoặc hết hạn, tạo session mới
    new_session_id = f"esp32-{device.device_id}-{secrets.token_hex(4)}"
    new_session = ChatSession.objects.create(
        device=device,
        user=None, # Có thể gán user nếu thiết bị thuộc sở hữu của ai đó
        session_id=new_session_id,
        expires_at=now + timedelta(minutes=60),
        is_active=True
    )

    return JsonResponse({
        'status': 'success',
        'session_id': new_session.session_id,
        'expires_at': new_session.expires_at.isoformat(),
        'message': 'Đã tạo session mới'
    })

@csrf_exempt
def esp32_interact(request):
    """
    API chính để ESP32 gửi câu hỏi và nhận câu trả lời từ AI.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Chỉ chấp nhận phương thức POST'}, status=405)

    device, error_response = authenticate_device(request)
    if error_response:
        return error_response

    try:
        data = json.loads(request.body)
        query = data.get('query')
        session_id = data.get('session_id')

        if not query:
            return JsonResponse({'error': 'Thiếu tham số query'}, status=400)

        # 1. Kiểm tra session
        now = timezone.now()
        session = None
        if session_id:
            session = ChatSession.objects.filter(session_id=session_id, device=device).first()
        
        if not session or not session.is_valid():
            # Tự động tạo session mới nếu session_id gửi lên không hợp lệ hoặc hết hạn
            new_id = f"esp32-{device.device_id}-{secrets.token_hex(4)}"
            session = ChatSession.objects.create(
                device=device,
                session_id=new_id,
                expires_at=now + timedelta(minutes=60)
            )
            logger.info(f"Auto-created session {session.session_id} for device {device.device_id}")

        # 2. Xử lý qua AI (Sử dụng chung logic với WebSocket nhưng trả về JSON đồng bộ cho ESP32)
        from .rag_mcp_integration import rag_mcp_service
        
        user_id = session.user_id if session.user_id else (device.owner_id if hasattr(device, 'owner_id') else None)
        full_response, tool_used = rag_mcp_service.process_sync_query(query, session.session_id, user_id=user_id)

        # 3. Trả về kết quả
        return JsonResponse({
            'status': 'success',
            'session_id': session.session_id,
            'response': full_response,
            'tool_used': tool_used,
            'timestamp': timezone.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error in ESP32 interaction: {e}")
        return JsonResponse({'error': str(e)}, status=500)
