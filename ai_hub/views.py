from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.contrib.auth.decorators import permission_required, login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.contrib import messages
import json
from django.db import models
from .models import ESP32Device, SensorData, DeviceCommand, MCPServer, ChatSession, ChatMessage, AIConfiguration, DeviceControlLabel
from .forms import MCPServerForm, AIConfigurationForm, DeviceControlLabelForm
from .rag_mcp_integration import rag_mcp_service
from .ai_service import get_ai_service
import sys
import os
import tempfile
import time
import numpy as np
import threading
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.conf import settings

# Add rag-mcp to Python path for RAG database
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'rag-mcp'))

# --- LLM CONCURRENCY CONTROL ---
llm_lock = threading.Lock()

# --- LOCAL STT/TTS SETUP ---
stt_engine = None
tts_model = None

def load_local_models():
    """Load local STT and TTS models once at startup"""
    global stt_engine, tts_model
    if stt_engine is None:
        try:
            import speech_recognition as sr
            stt_engine = sr.Recognizer()
        except Exception:
            stt_engine = None
    if tts_model is None:
        try:
            from gtts import gTTS
            tts_model = gTTS
        except Exception:
            tts_model = None

load_local_models()

def get_chat_history(session, limit=5):
    """Get recent chat history for context window"""
    recent_messages = ChatMessage.objects.filter(session=session).order_by('-timestamp')[:limit]
    messages = []
    for msg in reversed(recent_messages):
        messages.append({"role": "user", "content": msg.query})
        messages.append({"role": "assistant", "content": msg.response})
    return messages

@login_required
def create_mcp_server(request):
    if request.method == 'POST':
        form = MCPServerForm(request.POST, user=request.user)
        if form.is_valid():
            mcp_server = form.save(commit=False)
            builtin_kind = form.cleaned_data.get("builtin_kind")
            if builtin_kind:
                mcp_server.domain = request.build_absolute_uri(f"/ai/mcp/builtin/{builtin_kind}/{mcp_server.device_id}").rstrip("/")
            if mcp_server.server_type == 'private':
                mcp_server.owner = request.user
            else:
                mcp_server.is_public = True
                mcp_server.owner = None
            mcp_server.save()
            messages.success(request, f"MCP Server '{mcp_server.name}' đã được tạo thành công!")
            return redirect('mcp_dashboard')
    else:
        form = MCPServerForm(initial={}, user=request.user)
    return render(request, 'ai_hub/create_mcp_server.html', {'form': form, 'is_admin': request.user.is_superuser})

@login_required
def mcp_dashboard(request):
    """
    MCP Dashboard: Chỉ Superuser mới được quản lý Node/Server.
    User thường sẽ được chuyển hướng thẳng tới Thư viện Công cụ.
    """
    if not request.user.is_superuser:
        return redirect('mcp_public_tools')
        
    from .models import MCPServer
    servers = MCPServer.objects.filter(is_active=True)
    
    context = {
        'total_servers': servers.count(),
        'online_servers': servers.filter(last_seen__gte=timezone.now() - timezone.timedelta(minutes=5)).count(),
        'public_servers': servers.filter(is_public=True).count(),
        'private_servers': servers.filter(is_public=False).count(),
        'recent_servers': servers.order_by('-last_seen')[:5]
    }
    return render(request, 'ai_hub/mcp_dashboard.html', context)

@login_required
def dashboard_view(request):
    if request.user.is_superuser:
        mcp_qs = MCPServer.objects.filter(is_active=True)
        devices = ESP32Device.objects.all()
        recent_data = SensorData.objects.all().order_by('-timestamp')[:10]
        chart_data_qs = SensorData.objects.all().order_by('-timestamp')[:30]
    else:
        mcp_qs = MCPServer.objects.filter(owner=request.user, is_active=True)
        user_sessions = ChatSession.objects.filter(user=request.user).values_list('device_id', flat=True)
        devices = ESP32Device.objects.filter(id__in=user_sessions, is_active=True)
        recent_data = SensorData.objects.filter(device__in=devices).order_by('-timestamp')[:10]
        chart_data_qs = SensorData.objects.filter(device__in=devices).order_by('-timestamp')[:30]
    
    mcp_stats = {
        'total_servers': mcp_qs.count(),
        'online_servers': mcp_qs.filter(last_seen__gte=timezone.now() - timezone.timedelta(minutes=5)).count(),
        'private_servers': mcp_qs.filter(server_type='private').count(),
        'public_servers': mcp_qs.filter(server_type='public').count()
    }
    
    chart_list = list(reversed(chart_data_qs))
    chart_labels = [d.timestamp.strftime('%H:%M:%S') for d in chart_list]
    chart_values = [d.value for d in chart_list]
    chart_unit = chart_list[0].unit if chart_list else ""
    chart_sensor_type = chart_list[0].get_sensor_type_display() if chart_list else "Sensor"

    return render(request, 'ai_hub/dashboard.html', {
        'devices': devices, 'recent_data': recent_data, 'mcp_stats': mcp_stats,
        'chart_labels': json.dumps(chart_labels), 'chart_values': json.dumps(chart_values),
        'chart_unit': chart_unit, 'chart_sensor_type': chart_sensor_type,
    })

@csrf_exempt
def chat_interface(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            query = data.get('query', '')
            session_id = data.get('session_id', '').strip()
            
            if not session_id:
                session_id = request.session.get('chat_session_id')
            
            user = getattr(request, 'user', None) if request.user.is_authenticated else None
            if not session_id:
                import uuid
                session_id = str(uuid.uuid4())
                session = ChatSession.objects.create(user=user, session_id=session_id)
                request.session['chat_session_id'] = session.session_id
            else:
                session, _ = ChatSession.objects.get_or_create(session_id=session_id, defaults={'user': user})
            
            query_str = str(query or "").strip()
            if query_str.lower().startswith("/mcp"):
                # Handle direct /mcp command if needed (omitted for brevity, can be restored if used)
                pass

            # RAG-MCP Processing via WebSocket is preferred, but this is the HTTP fallback
            import time
            import ollama
            start_time = time.time()
            
            user_id = user.id if user else None
            selected_tool = rag_mcp_service._check_metadata_query(query_str)
            if not selected_tool:
                selected_tool, _ = rag_mcp_service.dispatcher.smart_route(query_str)
            
            if selected_tool != "general_chat":
                # Note: this needs to be run in a way that handles the async nature of _check_user_tool_access
                # For simplicity in HTTP fallback, we might skip or use sync_to_async
                from asgiref.sync import async_to_sync
                has_access, error_msg = async_to_sync(rag_mcp_service._check_user_tool_access)(user_id, selected_tool)
                if not has_access:
                    return JsonResponse({'response': error_msg, 'tool_used': 'access_denied'})

            if selected_tool in rag_mcp_service.dispatcher.tools:
                handler = rag_mcp_service.dispatcher.tools[selected_tool]["handler"]
                prompt = handler(query_str, rag_mcp_service.retriever) if selected_tool == "rag_search" else handler(query_str)
            else:
                prompt = query_str

            chat_history = get_chat_history(session, limit=5)
            messages = chat_history + [{"role": "user", "content": prompt}]
            
            with llm_lock:
                response = ollama.chat(model="qwen2.5:1.5b", messages=messages, options={"temperature": 0.1})
                full_response = response['message']['content']
            
            ChatMessage.objects.create(session=session, query=query_str, response=full_response, tool_used=selected_tool, response_time=time.time()-start_time)
            return JsonResponse({'response': full_response, 'tool_used': selected_tool, 'response_time': time.time()-start_time})
            
        except Exception as e:
            return JsonResponse({'response': f'Lỗi: {str(e)}', 'tool_used': 'error'}, status=500)
    
    return render(request, 'ai_hub/chat.html')

@login_required
def mcp_public_tools(request):
    """Giao diện Trung tâm Công cụ MCP - Duyệt, thêm và gỡ bỏ công cụ"""
    from .models import MCPTool, UserMCPTool
    public_tools = MCPTool.objects.filter(is_enabled=True, is_public=True).order_by('-priority', 'category', 'display_name')
    user_tool_ids = UserMCPTool.objects.filter(user=request.user, is_active=True).values_list('tool_id', flat=True)
    
    categories = {}
    for tool in public_tools:
        cat = tool.category or "General"
        if cat not in categories: categories[cat] = []
        categories[cat].append({'tool': tool, 'is_added': tool.id in user_tool_ids})
    
    return render(request, 'ai_hub/mcp_public_tools.html', {
        'categories': categories, 
        'total_tools': public_tools.count(),
        'my_tools_count': len(user_tool_ids), 
        'page_title': 'Trung tâm Công cụ AI'
    })

@login_required
def mcp_my_tools(request):
    """Đã hợp nhất vào mcp_public_tools, redirect về đó"""
    return redirect('mcp_public_tools')

@login_required
@require_http_methods(["POST"])
def mcp_tool_add(request, tool_name):
    from .models import MCPTool, UserMCPTool
    tool = get_object_or_404(MCPTool, name=tool_name, is_enabled=True, is_public=True)
    user_tool, created = UserMCPTool.objects.get_or_create(user=request.user, tool=tool, defaults={'is_active': True})
    if not created and not user_tool.is_active:
        user_tool.is_active = True
        user_tool.save()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': f"Đã thêm {tool.display_name}"})
    messages.success(request, f"Đã thêm công cụ '{tool.display_name}' vào bộ sưu tập của bạn.")
    return redirect('mcp_public_tools')

@login_required
@require_http_methods(["POST"])
def mcp_tool_remove(request, tool_name):
    from .models import MCPTool, UserMCPTool
    tool = get_object_or_404(MCPTool, name=tool_name)
    UserMCPTool.objects.filter(user=request.user, tool=tool).delete()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': f"Đã gỡ {tool.display_name}"})
    messages.success(request, f"Đã gỡ công cụ '{tool.display_name}' khỏi bộ sưu tập.")
    return redirect('mcp_public_tools')

@csrf_exempt
@require_http_methods(["GET"])
def get_chat_history_api(request, session_id):
    """API lấy lịch sử chat theo session_id cho frontend"""
    try:
        session = ChatSession.objects.filter(session_id=session_id).first()
        if not session:
            return JsonResponse({'success': True, 'data': [], 'total_messages': 0})
        
        # Security Check
        if not request.user.is_superuser:
            if session.user_id and session.user_id != request.user.id:
                # Session belongs to another user
                return JsonResponse({'success': False, 'error': 'Permission denied', 'data': []}, status=403)
            
            # If session is anonymous (no user) and current user is logged in, link it
            if not session.user_id and request.user.is_authenticated:
                session.user = request.user
                session.save(update_fields=['user'])
        
        messages = ChatMessage.objects.filter(session=session).order_by('timestamp')
        history_data = [{
            'id': msg.id, 'query': msg.query, 'response': msg.response,
            'tool_used': msg.tool_used, 'timestamp': msg.timestamp.isoformat(),
            'response_time': msg.response_time
        } for msg in messages]
        return JsonResponse({'success': True, 'data': history_data, 'total_messages': len(history_data)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def ai_config_create(request):
    if request.method == 'POST':
        form = AIConfigurationForm(request.POST, user=request.user)
        if form.is_valid():
            config = form.save(commit=False)
            config.user = request.user
            config.save()
            messages.success(request, f"Cấu hình '{config.name}' đã được tạo!")
            return redirect('ai_config_list')
    else:
        form = AIConfigurationForm(initial={'name': f'Cấu hình của {request.user.username}'}, user=request.user)
    return render(request, 'ai_hub/ai_config_form.html', {'form': form, 'title': 'Tạo Cấu Hình AI Mới'})

@login_required
def ai_config_list(request):
    configs = AIConfiguration.objects.filter(models.Q(user=request.user) | models.Q(user__isnull=True)).order_by('-is_default', '-created_at')
    
    # Lấy config đang active thực tế của user này (theo logic fallback)
    active_config = AIConfiguration.objects.filter(user=request.user, is_default=True, is_active=True).first()
    if not active_config:
        active_config = AIConfiguration.objects.filter(user__isnull=True, is_default=True, is_active=True).first()
    if not active_config:
        active_config = AIConfiguration.objects.filter(is_active=True).first()
        
    return render(request, 'ai_hub/ai_config_list.html', {
        'configs': configs, 
        'config_count': configs.count(),
        'active_config_id': active_config.id if active_config else None
    })

@login_required
def ai_config_edit(request, pk):
    config = get_object_or_404(AIConfiguration, pk=pk)
    if not request.user.is_superuser and config.user != request.user:
        messages.error(request, "Bạn không có quyền!")
        return redirect('ai_config_list')
    if request.method == 'POST':
        form = AIConfigurationForm(request.POST, instance=config, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Cấu hình '{config.name}' đã được cập nhật!")
            return redirect('ai_config_list')
    else:
        form = AIConfigurationForm(instance=config, user=request.user)
    return render(request, 'ai_hub/ai_config_form.html', {'form': form, 'config': config, 'title': f'Chỉnh sửa {config.name}'})

@login_required
def ai_config_delete(request, pk):
    config = get_object_or_404(AIConfiguration, pk=pk)
    if not request.user.is_superuser and config.user != request.user:
        messages.error(request, "Bạn không có quyền!")
        return redirect('ai_config_list')
    if request.method == 'POST':
        config.delete()
        messages.success(request, "Cấu hình đã được xóa!")
        return redirect('ai_config_list')
    return render(request, 'ai_hub/ai_config_delete.html', {'config': config})

@login_required
def ai_config_set_default(request, pk):
    config = get_object_or_404(AIConfiguration, pk=pk)
    if not request.user.is_superuser and config.user != request.user:
        messages.error(request, "Bạn không có quyền!")
        return redirect('ai_config_list')
    config.is_default = True
    config.save()
    messages.success(request, f"'{config.name}' đã được đặt làm mặc định!")
    return redirect('ai_config_list')

@csrf_exempt
def get_active_ai_config(request):
    try:
        user = getattr(request, 'user', None)
        config = None
        if user and user.is_authenticated:
            config = AIConfiguration.objects.filter(user=user, is_default=True, is_active=True).first()
        if not config:
            config = AIConfiguration.objects.filter(user__isnull=True, is_default=True, is_active=True).first()
        if not config:
            config = AIConfiguration.objects.filter(is_active=True).first()
        
        if config:
            return JsonResponse({'success': True, 'config': {
                'id': config.id, 
                'name': config.name, 
                'stt_engine': config.get_stt_engine_display(),
                'stt_language': config.get_stt_language_display(),
                'stt_custom_url': config.stt_custom_url,
                'llm_model': config.llm_model, 
                'llm_temperature': config.llm_temperature,
                'tts_engine': config.get_tts_engine_display(),
                'tts_voice': config.get_tts_voice_display(), 
                'tts_speed': config.tts_speed,
                'tts_custom_url': config.tts_custom_url,
                'response_language': config.get_response_language_display()
            }})
        return JsonResponse({'success': False, 'error': 'No config found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def api_mcp_tools(request):
    """API endpoint để lấy danh sách MCP tools (Gồm tool hệ thống và tool user đã thêm)"""
    try:
        user = request.user if request.user.is_authenticated else None
        if not user:
            return JsonResponse({'success': False, 'error': 'Auth required'}, status=401)
        
        from .models import MCPTool, UserMCPTool
        from django.db.models import Q
        
        # 1. Lấy tool hệ thống (Luôn có sẵn)
        system_tools = MCPTool.objects.filter(is_enabled=True, is_system=True)
        
        # 2. Lấy tool user đã thêm
        user_tools_ids = UserMCPTool.objects.filter(user=user, is_active=True).values_list('tool_id', flat=True)
        user_added_tools = MCPTool.objects.filter(id__in=user_tools_ids, is_enabled=True)
        
        # 3. Hợp nhất
        all_available_tools = (system_tools | user_added_tools).distinct().order_by('category', 'display_name')
        
        tools = [{
            'name': t.name,
            'display_name': t.display_name,
            'description': t.description,
            'icon': t.icon,
            'category': t.category,
            'quick_command': t.quick_command,
            'color_class': t.color_class or 'border-secondary text-secondary',
            'tool_type': t.tool_type
        } for t in all_available_tools]
        
        categories = {}
        for tool in tools:
            cat = tool.get('category', 'General')
            if cat not in categories: categories[cat] = []
            categories[cat].append(tool)
            
        return JsonResponse({'success': True, 'tools': tools, 'categories': categories, 'count': len(tools)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def clear_chat_history(request, session_id=None):
    if session_id:
        session = get_object_or_404(ChatSession, session_id=session_id)
        if session.user == request.user or request.user.is_superuser:
            ChatMessage.objects.filter(session=session).delete()
            messages.success(request, "Đã xóa lịch sử hội thoại.")
    else:
        ChatMessage.objects.filter(session__user=request.user).delete()
        messages.success(request, "Đã xóa toàn bộ lịch sử.")
    return redirect('ai_chat')

@login_required
def device_management(request):
    return render(request, 'ai_hub/devices.html', {'devices': ESP32Device.objects.all()})

@login_required
def device_detail(request, device_id):
    device = get_object_or_404(ESP32Device, device_id=device_id)
    return render(request, 'ai_hub/device_detail.html', {'device': device, 'labels': device.labels.all(), 'form': DeviceControlLabelForm()})

@login_required
def add_device_label(request, device_id):
    device = get_object_or_404(ESP32Device, device_id=device_id)
    if request.method == 'POST':
        form = DeviceControlLabelForm(request.POST)
        if form.is_valid():
            label = form.save(commit=False)
            label.device = device
            label.save()
            messages.success(request, "Đã thêm nhãn.")
    return redirect('device_detail', device_id=device_id)

@login_required
def delete_device_label(request, pk):
    label = get_object_or_404(DeviceControlLabel, pk=pk)
    device_id = label.device.device_id
    label.delete()
    return redirect('device_detail', device_id=device_id)

@login_required
def delete_device(request, device_id):
    if request.user.is_superuser:
        get_object_or_404(ESP32Device, device_id=device_id).delete()
        messages.success(request, "Đã xóa thiết bị.")
    return redirect('device_management')

@login_required
def sensor_data_view(request, device_id=None):
    if device_id:
        device = get_object_or_404(ESP32Device, device_id=device_id)
        qs = SensorData.objects.filter(device=device).order_by('-timestamp')[:30]
    else:
        device = None
        qs = SensorData.objects.all().order_by('-timestamp')[:30]
    chart_list = list(reversed(qs))
    return render(request, 'ai_hub/sensor_data.html', {
        'device': device, 'sensor_data': qs,
        'chart_labels': json.dumps([d.timestamp.strftime('%H:%M:%S') for d in chart_list]),
        'chart_values': json.dumps([d.value for d in chart_list])
    })

@login_required
def delete_sensor_data(request, device_id=None):
    if request.user.is_superuser:
        if device_id: SensorData.objects.filter(device__device_id=device_id).delete()
        else: SensorData.objects.all().delete()
    return redirect('sensor_data')

@csrf_exempt
def voice_chat(request):
    # Simplified voice chat for ESP32/Mobile HTTP fallback
    return JsonResponse({'status': 'ok', 'message': 'Voice chat processed via WebSocket is recommended'})

@csrf_exempt
def mqtt_webhook(request):
    return JsonResponse({'status': 'ok'})

@login_required
def send_device_command(request, device_id):
    if request.method == 'POST':
        device = get_object_or_404(ESP32Device, device_id=device_id)
        data = json.loads(request.body)
        cmd = DeviceCommand.objects.create(device=device, command=data.get('command'), parameters=data.get('parameters', {}), status='pending')
        return JsonResponse({'status': 'success', 'command_id': cmd.id})
    return JsonResponse({'status': 'error'}, status=405)
