from django import forms
from django.http import JsonResponse, StreamingHttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.contrib import messages
from django.db.models import Q, Count
import json
from .models import ESP32Device, SensorData, DeviceCommand, MCPServer, ChatSession, ChatMessage, AIConfiguration, STTConfiguration, LLMConfiguration, TTSConfiguration, DeviceControlLabel
from .forms import MCPServerForm, AIConfigurationForm, STTConfigurationForm, LLMConfigurationForm, TTSConfigurationForm, DeviceControlLabelForm
from .rag_mcp_integration import rag_mcp_service

@login_required
def create_mcp_server(request):
    if request.method == 'POST':
        form = MCPServerForm(request.POST, user=request.user)
        if form.is_valid():
            mcp_server = form.save(commit=False)
            
            # Mặc định là private và gán owner
            mcp_server.server_type = 'private'
            mcp_server.owner = request.user
            
            # Kiểm tra nếu là URL local (localhost/127.0.0.1) thì đánh dấu là local managed
            domain = mcp_server.domain or ""
            if "localhost" in domain or "127.0.0.1" in domain:
                mcp_server.server_type = 'local'
                mcp_server.is_local_managed = True
            
            mcp_server.save()
            messages.success(request, f"MCP Server '{mcp_server.name}' đã được tạo thành công!")
            return redirect('mcp_dashboard')
    else:
        form = MCPServerForm(initial={}, user=request.user)
    return render(request, 'ai_hub/create_mcp_server.html', {'form': form, 'is_admin': request.user.is_superuser})

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
        'public_servers': mcp_qs.filter(server_type='public').count(),
        'local_servers': mcp_qs.filter(server_type='local').count()
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
        'has_chart_data': len(chart_list) > 0,
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

            # Dùng pipeline sync của rag_mcp_service thay vì gọi trực tiếp Ollama
            user_id = user.id if user else None
            full_response, selected_tool = rag_mcp_service.process_sync_query(
                query=query_str,
                session_id=session.session_id,
                user_id=user_id,
            )
            return JsonResponse({'response': full_response, 'tool_used': selected_tool})
            
        except Exception as e:
            return JsonResponse({'response': f'Lỗi: {str(e)}', 'tool_used': 'error'}, status=500)
    
    return render(request, 'ai_hub/chat.html')

@login_required
def mcp_public_tools(request):
    """Giao diện Trung tâm Công cụ AI - Tools + Knowledge Bases"""
    from .models import MCPTool, UserMCPTool, KnowledgeBase, UserKnowledgeBase

    # --- Tools ---
    public_tools = MCPTool.objects.filter(
        is_enabled=True,
        is_visible=True,
        source_server__isnull=False,
        source_server__is_active=True,
    ).exclude(
        Q(name__icontains='rag_search') | Q(name__icontains='help_info')
    ).select_related('source_server').order_by('-priority', 'category', 'display_name')

    user_tool_ids = set(
        UserMCPTool.objects.filter(
            user=request.user,
            is_active=True,
            tool__is_enabled=True,
            tool__source_server__isnull=False,
            tool__source_server__is_active=True,
        ).values_list('tool_id', flat=True)
    )

    tool_categories = {}
    for tool in public_tools:
        cat = tool.category or "General"
        if cat not in tool_categories:
            tool_categories[cat] = []
        tool_categories[cat].append({'tool': tool, 'is_added': tool.id in user_tool_ids, 'can_toggle': tool.is_public})

    # --- Knowledge Bases ---
    public_kbs = KnowledgeBase.objects.filter(is_public=True).order_by('-is_system', 'category', 'name')
    user_kb_ids = set(
        UserKnowledgeBase.objects.filter(user=request.user, is_active=True).values_list('kb_id', flat=True)
    )

    kb_categories = {}
    for kb in public_kbs:
        cat = kb.category or "General"
        if cat not in kb_categories:
            kb_categories[cat] = []
        kb_categories[cat].append({'kb': kb, 'is_added': kb.id in user_kb_ids})

    return render(request, 'ai_hub/mcp_public_tools.html', {
        'tool_categories': tool_categories,
        'kb_categories': kb_categories,
        'total_tools': public_tools.count(),
        'my_tools_count': len(user_tool_ids),
        'total_kbs': public_kbs.count(),
        'my_kbs_count': len(user_kb_ids),
        'page_title': 'Trung tâm Công cụ AI',
    })

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


@login_required
@require_http_methods(["POST"])
def kb_add(request, kb_id):
    from .models import KnowledgeBase, UserKnowledgeBase
    kb = get_object_or_404(KnowledgeBase, id=kb_id, is_public=True)
    user_kb, created = UserKnowledgeBase.objects.get_or_create(user=request.user, kb=kb, defaults={'is_active': True})
    if not created and not user_kb.is_active:
        user_kb.is_active = True
        user_kb.save()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': f"Đã thêm {kb.name}"})
    messages.success(request, f"Đã thêm bộ tri thức '{kb.name}'.")
    return redirect('mcp_public_tools')


@login_required
@require_http_methods(["POST"])
def kb_remove(request, kb_id):
    from .models import KnowledgeBase, UserKnowledgeBase
    kb = get_object_or_404(KnowledgeBase, id=kb_id)
    UserKnowledgeBase.objects.filter(user=request.user, kb=kb).delete()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': f"Đã gỡ {kb.name}"})
    messages.success(request, f"Đã gỡ bộ tri thức '{kb.name}'.")
    return redirect('mcp_public_tools')


@login_required
@require_http_methods(["GET"])
def kb_user_list_api(request):
    """API trả về danh sách KB mà user đang dùng (active + system)."""
    from .models import KnowledgeBase, UserKnowledgeBase
    system_kbs = list(KnowledgeBase.objects.filter(is_system=True).values(
        'id', 'name', 'description', 'namespace', 'icon', 'color_class', 'category'
    ))
    user_kb_ids = set(UserKnowledgeBase.objects.filter(
        user=request.user, is_active=True
    ).values_list('kb_id', flat=True))
    user_kbs = list(KnowledgeBase.objects.filter(
        id__in=user_kb_ids, is_system=False
    ).values('id', 'name', 'description', 'namespace', 'icon', 'color_class', 'category'))

    return JsonResponse({
        'success': True,
        'system_kbs': system_kbs,
        'user_kbs': user_kbs,
    })

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

# AI Configuration Views - NEW ARCHITECTURE

@login_required
def stt_config_list(request):
    """Danh sách STT Configurations"""
    configs = STTConfiguration.objects.all().order_by('-is_active', 'name')
    return render(request, 'ai_hub/stt_config_list.html', {
        'configs': configs, 
        'config_count': configs.count()
    })

@login_required
def stt_config_create(request):
    """Tạo STT Configuration mới"""
    if request.method == 'POST':
        form = STTConfigurationForm(request.POST)
        if form.is_valid():
            config = form.save()
            messages.success(request, f"Cấu hình STT '{config.name}' đã được tạo!")
            return redirect('stt_config_list')
    else:
        form = STTConfigurationForm()
    return render(request, 'ai_hub/stt_config_form.html', {'form': form, 'title': 'Tạo Cấu Hình STT Mới'})

@login_required
def stt_config_edit(request, pk):
    """Chỉnh sửa STT Configuration"""
    config = get_object_or_404(STTConfiguration, pk=pk)
    if request.method == 'POST':
        form = STTConfigurationForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, f"Cấu hình STT '{config.name}' đã được cập nhật!")
            return redirect('stt_config_list')
    else:
        form = STTConfigurationForm(instance=config)
    return render(request, 'ai_hub/stt_config_form.html', {'form': form, 'config': config, 'title': f'Chỉnh sửa {config.name}'})

@login_required
def stt_config_delete(request, pk):
    """Xóa STT Configuration"""
    config = get_object_or_404(STTConfiguration, pk=pk)
    if request.method == 'POST':
        name = config.name
        config.delete()
        messages.success(request, f"Cấu hình STT '{name}' đã được xóa!")
        return redirect('stt_config_list')
    return render(request, 'ai_hub/stt_config_delete.html', {'config': config})


@login_required
def llm_config_list(request):
    """Danh sách LLM Configurations"""
    configs = LLMConfiguration.objects.all().order_by('-is_active', 'name')
    return render(request, 'ai_hub/llm_config_list.html', {
        'configs': configs, 
        'config_count': configs.count()
    })

@login_required
def llm_config_create(request):
    """Tạo LLM Configuration mới"""
    if request.method == 'POST':
        form = LLMConfigurationForm(request.POST)
        if form.is_valid():
            config = form.save()
            messages.success(request, f"Cấu hình LLM '{config.name}' đã được tạo!")
            return redirect('llm_config_list')
    else:
        form = LLMConfigurationForm()
    return render(request, 'ai_hub/llm_config_form.html', {'form': form, 'title': 'Tạo Cấu Hình LLM Mới'})

@login_required
def llm_config_edit(request, pk):
    """Chỉnh sửa LLM Configuration"""
    config = get_object_or_404(LLMConfiguration, pk=pk)
    if request.method == 'POST':
        form = LLMConfigurationForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, f"Cấu hình LLM '{config.name}' đã được cập nhật!")
            return redirect('llm_config_list')
    else:
        form = LLMConfigurationForm(instance=config)
    return render(request, 'ai_hub/llm_config_form.html', {'form': form, 'config': config, 'title': f'Chỉnh sửa {config.name}'})

@login_required
def llm_config_delete(request, pk):
    """Xóa LLM Configuration"""
    config = get_object_or_404(LLMConfiguration, pk=pk)
    if request.method == 'POST':
        name = config.name
        config.delete()
        messages.success(request, f"Cấu hình LLM '{name}' đã được xóa!")
        return redirect('llm_config_list')
    return render(request, 'ai_hub/llm_config_delete.html', {'config': config})


@login_required
def tts_config_list(request):
    """Danh sách TTS Configurations"""
    configs = TTSConfiguration.objects.all().order_by('-is_active', 'name')
    return render(request, 'ai_hub/tts_config_list.html', {
        'configs': configs, 
        'config_count': configs.count()
    })

@login_required
def tts_config_create(request):
    """Tạo TTS Configuration mới"""
    if request.method == 'POST':
        form = TTSConfigurationForm(request.POST)
        if form.is_valid():
            config = form.save()
            messages.success(request, f"Cấu hình TTS '{config.name}' đã được tạo!")
            return redirect('tts_config_list')
    else:
        form = TTSConfigurationForm()
    return render(request, 'ai_hub/tts_config_form.html', {'form': form, 'title': 'Tạo Cấu Hình TTS Mới'})

@login_required
def tts_config_edit(request, pk):
    """Chỉnh sửa TTS Configuration"""
    config = get_object_or_404(TTSConfiguration, pk=pk)
    if request.method == 'POST':
        form = TTSConfigurationForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, f"Cấu hình TTS '{config.name}' đã được cập nhật!")
            return redirect('tts_config_list')
    else:
        form = TTSConfigurationForm(instance=config)
    return render(request, 'ai_hub/tts_config_form.html', {'form': form, 'config': config, 'title': f'Chỉnh sửa {config.name}'})

@login_required
def tts_config_delete(request, pk):
    """Xóa TTS Configuration"""
    config = get_object_or_404(TTSConfiguration, pk=pk)
    if request.method == 'POST':
        name = config.name
        config.delete()
        messages.success(request, f"Cấu hình TTS '{name}' đã được xóa!")
        return redirect('tts_config_list')
    return render(request, 'ai_hub/tts_config_delete.html', {'config': config})


@login_required
def ai_config_list(request):
    """Danh sách AI Configurations tổng hợp"""
    configs = AIConfiguration.objects.filter(
        Q(user=request.user) | Q(user__isnull=True)
    ).order_by('-is_default', 'name')
    
    # Lấy config đang active thực tế của user này (theo logic fallback)
    active_config = AIConfiguration.objects.filter(
        user=request.user, is_default=True, is_active=True
    ).first()
    if not active_config:
        active_config = AIConfiguration.objects.filter(
            user__isnull=True, is_default=True, is_active=True
        ).first()
    if not active_config:
        active_config = AIConfiguration.objects.filter(
            is_active=True
        ).first()
        
    return render(request, 'ai_hub/ai_config_list.html', {
        'configs': configs, 
        'config_count': configs.count(),
        'active_config_id': active_config.id if active_config else None
    })

def _clone_sub_configs(source_ai_config, suffix=""):
    """Clone STT/LLM/TTS sub-configs từ một AIConfiguration, trả về (stt, llm, tts) mới."""

    def _clone(obj, name_suffix):
        if obj is None:
            return None
        # Refresh từ DB để đảm bảo có đầy đủ data
        obj = obj.__class__.objects.get(pk=obj.pk)
        obj.pk = None
        obj.id = None
        obj.name = f"{obj.name}{name_suffix}"
        obj.save()
        return obj

    stt = _clone(source_ai_config.stt_config, suffix)
    llm = _clone(source_ai_config.llm_config, suffix)
    tts = _clone(source_ai_config.tts_config, suffix)
    return stt, llm, tts


def _get_or_create_default_sub_configs(suffix=""):
    """Lấy sub-configs đầu tiên có sẵn hoặc tạo mới với giá trị mặc định."""

    def _clone(obj, name_suffix):
        if obj is None:
            return None
        obj = obj.__class__.objects.get(pk=obj.pk)
        obj.pk = None
        obj.id = None
        obj.name = f"{obj.name}{name_suffix}"
        obj.save()
        return obj

    stt = STTConfiguration.objects.first()
    llm = LLMConfiguration.objects.first()
    tts = TTSConfiguration.objects.first()
    return _clone(stt, suffix), _clone(llm, suffix), _clone(tts, suffix)


@login_required
def ai_config_create(request):
    """Tạo AI Configuration mới — tự động clone sub-configs từ global default."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip() or f'Cấu hình của {request.user.username}'
        is_default = request.POST.get('is_default') == 'on'
        description = request.POST.get('description', '')

        # Lấy global default để clone sub-configs
        global_default = AIConfiguration.objects.filter(
            user__isnull=True, is_active=True
        ).order_by('-is_default').first()

        if not global_default:
            global_default = AIConfiguration.objects.filter(is_active=True).first()

        if global_default:
            stt, llm, tts = _clone_sub_configs(global_default, suffix=f" ({request.user.username})")
        else:
            stt, llm, tts = _get_or_create_default_sub_configs(suffix=f" ({request.user.username})")

        config = AIConfiguration.objects.create(
            name=name,
            user=None if request.user.is_superuser and is_default else request.user,
            stt_config=stt,
            llm_config=llm,
            tts_config=tts,
            is_default=is_default,
            is_active=True,
            description=description,
        )
        messages.success(request, f"Cấu hình AI '{config.name}' đã được tạo! Hãy chỉnh sửa các thông số theo nhu cầu.")
        return redirect('ai_config_edit', pk=config.pk)

    return render(request, 'ai_hub/ai_config_create_simple.html', {
        'title': 'Tạo Cấu Hình AI Mới',
        'default_name': f'Cấu hình của {request.user.username}',
        'is_superuser': request.user.is_superuser,
    })

@login_required
def ai_config_edit(request, pk):
    """Chỉnh sửa AI Configuration — gộp STT/LLM/TTS inline"""
    from .forms import STTConfigurationForm, LLMConfigurationForm, TTSConfigurationForm
    config = get_object_or_404(AIConfiguration, pk=pk)
    if not request.user.is_superuser and config.user != request.user:
        messages.error(request, "Bạn không có quyền!")
        return redirect('ai_config_list')

    # Guard: nếu sub-config đang share với config khác thì clone riêng trước khi edit
    def _ensure_owned(sub_obj, fk_field):
        if sub_obj is None:
            return sub_obj
        shared = AIConfiguration.objects.filter(**{fk_field: sub_obj}).count() > 1
        if shared:
            sub_obj.pk = None
            sub_obj.name = f"{sub_obj.name} ({config.name})"
            sub_obj.save()
            setattr(config, fk_field, sub_obj)
            config.save(update_fields=[fk_field])
        return sub_obj

    stt = _ensure_owned(config.stt_config, 'stt_config')
    llm = _ensure_owned(config.llm_config, 'llm_config')
    tts = _ensure_owned(config.tts_config, 'tts_config')

    def _make_ai_form(data=None):
        f = AIConfigurationForm(data, instance=config, user=request.user)
        # Loại bỏ hoàn toàn FK fields khỏi validation — sẽ gán thủ công khi save
        for field_name in ('stt_config', 'llm_config', 'tts_config'):
            f.fields[field_name].widget = forms.HiddenInput()
            f.fields[field_name].required = False
            f.fields[field_name].queryset = f.fields[field_name].queryset.model.objects.all()
        return f

    if request.method == 'POST':
        form = _make_ai_form(request.POST)
        stt_form = STTConfigurationForm(request.POST, instance=stt, prefix='stt') if stt else None
        llm_form = LLMConfigurationForm(request.POST, instance=llm, prefix='llm') if llm else None
        tts_form = TTSConfigurationForm(request.POST, instance=tts, prefix='tts') if tts else None

        all_forms = [f for f in [form, stt_form, llm_form, tts_form] if f]
        forms_valid = all(f.is_valid() for f in all_forms)

        if forms_valid:
            if stt_form: stt_form.save()
            if llm_form: llm_form.save()
            if tts_form: tts_form.save()
            cfg = form.save(commit=False)
            # Luôn giữ nguyên FK — không cho user thay đổi qua hidden field
            cfg.stt_config = stt
            cfg.llm_config = llm
            cfg.tts_config = tts
            cfg.save()
            messages.success(request, f"Cấu hình '{config.name}' đã được cập nhật!")
            return redirect('ai_config_list')
        else:
            import logging
            _log = logging.getLogger(__name__)
            for f in all_forms:
                if f.errors:
                    _log.warning("[CONFIG_EDIT] Form errors: %s", f.errors)
    else:
        form = _make_ai_form()
        stt_form = STTConfigurationForm(instance=stt, prefix='stt') if stt else None
        llm_form = LLMConfigurationForm(instance=llm, prefix='llm') if llm else None
        tts_form = TTSConfigurationForm(instance=tts, prefix='tts') if tts else None

    return render(request, 'ai_hub/ai_config_form.html', {
        'form': form,
        'stt_form': stt_form,
        'llm_form': llm_form,
        'tts_form': tts_form,
        'config': config,
        'title': f'Chỉnh sửa {config.name}',
    })

@login_required
def ai_config_delete(request, pk):
    """Xóa AI Configuration"""
    config = get_object_or_404(AIConfiguration, pk=pk)
    if not request.user.is_superuser and config.user != request.user:
        messages.error(request, "Bạn không có quyền!")
        return redirect('ai_config_list')
    if request.method == 'POST':
        name = config.name
        config.delete()
        messages.success(request, f"Cấu hình AI '{name}' đã được xóa!")
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
            config = AIConfiguration.objects.select_related(
                'stt_config', 'llm_config', 'tts_config'
            ).filter(user=user, is_default=True, is_active=True).first()
        if not config:
            config = AIConfiguration.objects.select_related(
                'stt_config', 'llm_config', 'tts_config'
            ).filter(user__isnull=True, is_default=True, is_active=True).first()
        if not config:
            config = AIConfiguration.objects.select_related(
                'stt_config', 'llm_config', 'tts_config'
            ).filter(is_active=True).first()

        if config:
            stt = config.stt_config
            llm = config.llm_config
            tts = config.tts_config
            return JsonResponse({'success': True, 'config': {
                'id': config.id,
                'name': config.name,
                'stt_engine': stt.get_engine_display() if stt else '--',
                'stt_language': stt.get_language_display() if stt else '--',
                'stt_custom_url': stt.custom_url if stt else '',
                'llm_model': llm.model if llm else 'qwen2.5:1.5b',
                'llm_temperature': llm.temperature if llm else 0.1,
                'llm_router_model': llm.router_model if llm else 'qwen2.5:0.5b',
                'llm_router_timeout': llm.router_timeout if llm else 3,
                'tts_engine': tts.get_engine_display() if tts else '--',
                'tts_voice': tts.voice_id if tts else '--',
                'tts_speed': tts.speed if tts else 1.0,
                'tts_custom_url': tts.custom_url if tts else '',
                'response_language': llm.get_response_language_display() if llm else 'Tiếng Việt',
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
        
        # Chỉ lấy tools từ MCP server thực (có source_server) mà user đã thêm
        user_tools_ids = UserMCPTool.objects.filter(user=user, is_active=True).values_list('tool_id', flat=True)
        all_available_tools = MCPTool.objects.filter(
            id__in=user_tools_ids,
            is_enabled=True,
            source_server__isnull=False,
            source_server__is_active=True,
        ).distinct().order_by('category', 'display_name')
        
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
    if request.method != 'POST':
        return redirect('ai_chat')
    if session_id:
        # Xóa theo session_id từ URL
        session = get_object_or_404(ChatSession, session_id=session_id)
        if session.user == request.user or request.user.is_superuser:
            ChatMessage.objects.filter(session=session).delete()
            messages.success(request, "Đã xóa lịch sử hội thoại.")
    else:
        # Xóa tất cả messages của user (session có user gắn)
        ChatMessage.objects.filter(session__user=request.user).delete()
        # Xóa thêm session anonymous nếu client gửi session_id
        client_session_id = request.POST.get('session_id', '').strip()
        if client_session_id:
            anon_session = ChatSession.objects.filter(
                session_id=client_session_id, user__isnull=True
            ).first()
            if anon_session:
                ChatMessage.objects.filter(session=anon_session).delete()
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

@login_required
def send_device_command(request, device_id):
    if request.method == 'POST':
        import requests as http_requests
        device = get_object_or_404(ESP32Device, device_id=device_id)
        data = json.loads(request.body)
        command = data.get('command', '')
        parameters = data.get('parameters', {})

        cmd = DeviceCommand.objects.create(
            device=device, command=command, parameters=parameters, status='pending'
        )

        # Gửi lệnh HTTP trực tiếp đến thiết bị nếu có IP
        if device.ip_address:
            try:
                resp = http_requests.post(
                    f"http://{device.ip_address}/control",
                    json={"command": command, "parameters": parameters},
                    timeout=5
                )
                if resp.status_code == 200:
                    cmd.status = 'executed'
                    cmd.executed_at = timezone.now()
                    cmd.save()
                    return JsonResponse({'status': 'success', 'command_id': cmd.id, 'device_response': resp.json()})
                else:
                    cmd.status = 'failed'
                    cmd.save()
                    return JsonResponse({'status': 'error', 'message': f'Thiết bị trả về lỗi HTTP {resp.status_code}', 'command_id': cmd.id})
            except Exception as e:
                cmd.status = 'failed'
                cmd.save()
                return JsonResponse({'status': 'error', 'message': f'Không thể kết nối đến thiết bị: {str(e)}', 'command_id': cmd.id})
        else:
            cmd.status = 'sent'
            cmd.save()
            return JsonResponse({'status': 'success', 'command_id': cmd.id, 'message': 'Lệnh đã được lưu (thiết bị chưa có IP)'})
    return JsonResponse({'status': 'error', 'message': 'Phương thức không hợp lệ'}, status=405)


@csrf_exempt
@require_http_methods(["POST"])
def api_device_control(request):
    """API nội bộ cho tools-service gọi ngược để điều khiển thiết bị."""
    try:
        data = json.loads(request.body)
        query = data.get("query", "")
        query_lower = query.lower()

        from .models import DeviceControlLabel
        import requests as http_requests

        all_labels = DeviceControlLabel.objects.filter(is_active=True).select_related('device').order_by('-label')
        target_label = next((l for l in all_labels if l.label.lower() in query_lower), None)

        if not target_label:
            available = ", ".join(l.label for l in all_labels)
            return JsonResponse({"result": f"Không tìm thấy thiết bị phù hợp. Nhãn hiện có: {available or 'chưa có'}"})

        device = target_label.device
        if not device.ip_address:
            return JsonResponse({"result": f"Thiết bị '{device.name}' chưa có địa chỉ IP."})

        is_on = any(x in query_lower for x in ["bật", "mở", "bat", "mo", "on", "active"])
        is_off = any(x in query_lower for x in ["tắt", "đóng", "tat", "dong", "off", "stop"])
        action = "on" if is_on else "off" if is_off else None

        if not action:
            return JsonResponse({"result": f"Hãy nói rõ 'bật' hay 'tắt' cho '{target_label.label}'."})

        try:
            resp = http_requests.post(
                f"http://{device.ip_address}/control",
                json={"command": f"{target_label.channel}_{action}", "parameters": {}},
                timeout=5,
            )
            if resp.status_code == 200:
                status_text = "BẬT" if action == "on" else "TẮT"
                return JsonResponse({"result": f"Đã {status_text} '{target_label.label}' thành công!"})
            return JsonResponse({"result": f"Thiết bị trả về lỗi HTTP {resp.status_code}"})
        except Exception as e:
            return JsonResponse({"result": f"Không thể kết nối đến thiết bị: {str(e)}"})

    except Exception as e:
        return JsonResponse({"result": f"Lỗi hệ thống: {str(e)}"}, status=500)


@require_http_methods(["GET"])
def api_list_devices(request):
    """API nội bộ cho tools-service gọi ngược để liệt kê thiết bị."""
    try:
        from .models import ESP32Device
        devices = ESP32Device.objects.filter(is_active=True)
        if not devices.exists():
            return JsonResponse({"result": "Không có thiết bị nào đang hoạt động."})
        result = f"Tìm thấy {devices.count()} thiết bị:\n"
        for d in devices:
            is_online = d.last_seen and (timezone.now() - d.last_seen).total_seconds() < 300
            result += f"- {d.name}: {'Online' if is_online else 'Offline'}\n"
        return JsonResponse({"result": result.strip()})
    except Exception as e:
        return JsonResponse({"result": f"Lỗi: {str(e)}"}, status=500)


@login_required
def ping_device(request, device_id):
    """Kiểm tra kết nối đến thiết bị ESP32."""
    import requests as http_requests
    device = get_object_or_404(ESP32Device, device_id=device_id)
    if not device.ip_address:
        return JsonResponse({'status': 'error', 'message': 'Thiết bị chưa có địa chỉ IP'})
    try:
        resp = http_requests.get(f"http://{device.ip_address}/status", timeout=3)
        if resp.status_code == 200:
            device.last_seen = timezone.now()
            device.save(update_fields=['last_seen'])
            return JsonResponse({'status': 'success', 'message': 'Thiết bị đang online', 'data': resp.json()})
        return JsonResponse({'status': 'error', 'message': f'Thiết bị phản hồi HTTP {resp.status_code}'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Không thể kết nối: {str(e)}'})


# ---------------------------------------------------------------------------
# Internal API cho tools-service: system_tools
# ---------------------------------------------------------------------------

@require_http_methods(["GET"])
def api_user_info(request):
    """Trả thông tin user hiện tại — dùng X-API-Key hoặc session."""
    try:
        # Ưu tiên user từ session (nếu gọi qua browser/WebSocket context)
        user = request.user if request.user.is_authenticated else None

        # Fallback: tìm user qua query param user_id (tools-service truyền vào)
        if not user:
            uid = request.GET.get("user_id")
            if uid:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.filter(pk=uid).first()

        if not user:
            return JsonResponse({"result": "Không xác định được người dùng. Vui lòng đăng nhập."})

        profile = getattr(user, "profile", None)
        result = {
            "username": user.username,
            "full_name": user.get_full_name() or user.username,
            "email": user.email,
            "role": user.role_display,
            "phone": profile.phone if profile else None,
            "address": profile.address if profile else None,
        }
        return JsonResponse({"result": result})
    except Exception as e:
        return JsonResponse({"result": f"Lỗi: {str(e)}"}, status=500)


@require_http_methods(["GET"])
def api_list_products(request):
    """Liệt kê sản phẩm, có thể lọc theo từ khóa ?q=..."""
    try:
        from products.models import Product
        q = (request.GET.get("q") or "").strip()
        qs = Product.objects.filter(is_active=True)
        if q:
            qs = qs.filter(name__icontains=q)
        products = qs.order_by("name")[:20]
        if not products.exists():
            msg = f"Không tìm thấy sản phẩm nào" + (f" khớp với '{q}'" if q else "") + "."
            return JsonResponse({"result": msg})
        items = [
            {
                "name": p.name,
                "type": p.get_product_type_display(),
                "price": f"{p.price:,.0f} VNĐ",
                "stock": p.stock,
                "description": p.description[:100] if p.description else "",
            }
            for p in products
        ]
        return JsonResponse({"result": items})
    except Exception as e:
        return JsonResponse({"result": f"Lỗi: {str(e)}"}, status=500)


@require_http_methods(["GET"])
def api_order_status(request):
    """Trả trạng thái đơn hàng của user — cần user_id."""
    try:
        uid = request.GET.get("user_id")
        user = request.user if request.user.is_authenticated else None
        if not user and uid:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.filter(pk=uid).first()

        if not user:
            return JsonResponse({"result": "Không xác định được người dùng. Vui lòng đăng nhập."})

        from orders.models import Order
        orders = Order.objects.filter(user=user).select_related("product").order_by("-created_at")[:10]
        if not orders.exists():
            return JsonResponse({"result": "Bạn chưa có đơn hàng nào."})

        items = [
            {
                "order_id": o.id,
                "product": o.product.name,
                "status": o.get_status_display(),
                "total": f"{o.total:,.0f} VNĐ",
                "address": o.address or "Chưa có địa chỉ",
                "created_at": o.created_at.strftime("%d/%m/%Y"),
            }
            for o in orders
        ]
        return JsonResponse({"result": items})
    except Exception as e:
        return JsonResponse({"result": f"Lỗi: {str(e)}"}, status=500)


# ── Speech Service proxy ──────────────────────────────────────────────────────
import os as _os
import httpx as _httpx

SPEECH_SERVICE_URL = _os.environ.get("SPEECH_SERVICE_URL", "http://localhost:8003")


@csrf_exempt
@login_required
async def speech_stt_proxy(request):
    """Proxy audio blob từ browser lên speech-service (async để không block ASGI)."""
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    audio = request.FILES.get("audio")
    if not audio:
        return JsonResponse({"error": "Thiếu file audio"}, status=400)
    try:
        async with _httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{SPEECH_SERVICE_URL}/stt",
                files={"audio": (audio.name, audio.read(), audio.content_type)},
            )
        return JsonResponse(resp.json(), status=resp.status_code)
    except _httpx.ConnectError:
        return JsonResponse({"error": "Speech service chưa khởi động (port 8003)"}, status=503)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@login_required
async def speech_tts_proxy(request):
    """Proxy text → audio/wav từ speech-service (async)."""
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    import json as _json
    try:
        body = _json.loads(request.body)
        text = body.get("text", "").strip()
        speed = float(body.get("speed", 1.0))
    except Exception:
        return JsonResponse({"error": "Body JSON không hợp lệ"}, status=400)
    if not text:
        return JsonResponse({"error": "Thiếu text"}, status=400)
    try:
        async with _httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{SPEECH_SERVICE_URL}/tts",
                json={"text": text, "speed": speed},
            )
        return StreamingHttpResponse(
            (chunk for chunk in [resp.content]),
            content_type="audio/wav",
        )
    except _httpx.ConnectError:
        return JsonResponse({"error": "Speech service chưa khởi động (port 8003)"}, status=503)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ── RAG Document Upload ───────────────────────────────────────────────────────

RAG_SERVICE_URL = _os.environ.get("RAG_SERVICE_URL", "http://localhost:8001")
MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # 20MB
ALLOWED_EXTENSIONS = {'.pdf', '.txt', '.docx', '.md'}

import requests as _requests_sync


@login_required
@require_http_methods(["GET"])
def rag_document_list_api(request):
    """API trả về danh sách tài liệu của user hiện tại (JSON)."""
    from .models import UserDocument
    docs = UserDocument.objects.filter(user=request.user)
    return JsonResponse({
        'success': True,
        'documents': [
            {
                'id': d.id,
                'filename': d.filename,
                'file_type': d.file_type,
                'file_size': d.file_size,
                'chunk_count': d.chunk_count,
                'status': d.status,
                'uploaded_at': d.uploaded_at.strftime('%d/%m/%Y %H:%M'),
            }
            for d in docs
        ]
    })


@login_required
@require_http_methods(["POST"])
def rag_document_upload(request):
    """Upload file → ingest vào RAG service với namespace user_{id}."""
    from .models import UserDocument
    from pathlib import Path

    file = request.FILES.get('file')
    if not file:
        return JsonResponse({'success': False, 'error': 'Thiếu file'}, status=400)

    ext = Path(file.name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return JsonResponse({
            'success': False,
            'error': f'Định dạng không hỗ trợ. Chỉ chấp nhận: {", ".join(ALLOWED_EXTENSIONS)}'
        }, status=400)

    if file.size > MAX_UPLOAD_SIZE:
        return JsonResponse({
            'success': False,
            'error': f'File quá lớn (tối đa 20MB, file của bạn: {file.size // 1024 // 1024}MB)'
        }, status=400)

    namespace = f"user_{request.user.id}"

    # Đọc nội dung file trước (InMemoryUploadedFile chỉ đọc được 1 lần)
    file_content = file.read()

    # Tạo bản ghi pending, lưu file gốc vào media storage
    doc = UserDocument.objects.create(
        user=request.user,
        filename=file.name,
        file_type=ext.lstrip('.'),
        file_size=file.size,
        status='pending',
    )
    # Lưu file gốc để có thể re-ingest sau này
    from django.core.files.base import ContentFile
    doc.file.save(file.name, ContentFile(file_content), save=True)

    # Gọi RAG service
    try:
        resp = _requests_sync.post(
            f"{RAG_SERVICE_URL}/upload",
            files={'file': (file.name, file_content, file.content_type or 'application/octet-stream')},
            data={'namespace': namespace},
            timeout=60,
        )
        resp.raise_for_status()
        result = resp.json()
        chunk_count = result.get('chunks_added', result.get('chunks_indexed', 0))
        # status="skipped" nghĩa là file đã tồn tại và không thay đổi — vẫn coi là success
        if result.get('status') == 'skipped':
            doc.status = 'success'
            doc.save()
            return JsonResponse({'success': True, 'chunks': doc.chunk_count or 0, 'id': doc.id, 'skipped': True})
        if chunk_count == 0:
            doc.status = 'failed'
            doc.error_message = 'RAG service không index được nội dung (0 chunks). File có thể rỗng hoặc không đọc được.'
            doc.save()
            return JsonResponse({'success': False, 'error': doc.error_message}, status=422)
        doc.chunk_count = chunk_count
        doc.status = 'success'
        doc.save()
        # Cập nhật description của rag_search tool dựa trên nội dung thực tế
        import threading
        rag_mcp_service.ensure_rag_tool()
        threading.Thread(
            target=rag_mcp_service.refresh_rag_tool_description,
            args=(request.user.id,),
            daemon=True,
        ).start()
        return JsonResponse({'success': True, 'chunks': doc.chunk_count, 'id': doc.id})
    except _requests_sync.exceptions.ConnectionError:
        doc.status = 'failed'
        doc.error_message = 'RAG service chưa khởi động'
        doc.save()
        return JsonResponse({'success': False, 'error': 'RAG service chưa khởi động'}, status=503)
    except Exception as e:
        doc.status = 'failed'
        doc.error_message = str(e)
        doc.save()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def rag_document_delete(request, doc_id):
    """Xóa tài liệu và rebuild index của user."""
    from .models import UserDocument

    doc = get_object_or_404(UserDocument, pk=doc_id, user=request.user)
    doc.delete()

    namespace = f"user_{request.user.id}"
    remaining = UserDocument.objects.filter(user=request.user, status='success')

    if not remaining.exists():
        # Không còn tài liệu → xóa namespace trên RAG service
        try:
            _requests_sync.delete(f"{RAG_SERVICE_URL}/namespace/{namespace}", timeout=10)
        except Exception:
            pass
    else:
        # Còn tài liệu → refresh description để phản ánh nội dung còn lại
        import threading
        threading.Thread(
            target=rag_mcp_service.refresh_rag_tool_description,
            args=(request.user.id,),
            daemon=True,
        ).start()

    return JsonResponse({'success': True})


@login_required
@require_http_methods(["POST"])
def rag_reindex(request):
    """Re-ingest tất cả tài liệu của user lên RAG service (dùng khi index bị mất)."""
    from .models import UserDocument

    docs = UserDocument.objects.filter(user=request.user, status='success')
    if not docs.exists():
        return JsonResponse({'success': False, 'error': 'Không có tài liệu nào để re-ingest'}, status=400)

    namespace = f"user_{request.user.id}"
    success_count = 0
    failed = []

    for doc in docs:
        if not doc.file or not doc.file.name:
            failed.append({'filename': doc.filename, 'error': 'File gốc không còn trên server'})
            continue
        try:
            with doc.file.open('rb') as f:
                resp = _requests_sync.post(
                    f"{RAG_SERVICE_URL}/upload",
                    files={'file': (doc.filename, f.read(), 'application/octet-stream')},
                    data={'namespace': namespace},
                    timeout=60,
                )
            resp.raise_for_status()
            result = resp.json()
            chunk_count = result.get('chunks_added', result.get('chunks_indexed', 0))
            if chunk_count == 0:
                doc.status = 'failed'
                doc.error_message = 'RAG service không index được nội dung (0 chunks). File có thể rỗng hoặc không đọc được.'
                doc.save()
                failed.append({'filename': doc.filename, 'error': doc.error_message})
                continue
            doc.chunk_count = chunk_count
            doc.error_message = ''
            doc.save()
            success_count += 1
        except Exception as e:
            failed.append({'filename': doc.filename, 'error': str(e)})

    import threading
    threading.Thread(
        target=rag_mcp_service.refresh_rag_tool_description,
        args=(request.user.id,),
        daemon=True,
    ).start()

    return JsonResponse({'success': True, 'reindexed': success_count, 'failed': failed})

# ── Knowledge Base Admin ───────────────────────────────────────────────────────

def _auto_summarize_kb(kb_id: int):
    """
    Background task: lấy sample texts từ RAG rồi dùng LLM tóm tắt,
    lưu vào KnowledgeBase.description.
    """
    import django
    try:
        from .models import KnowledgeBase
        kb = KnowledgeBase.objects.get(id=kb_id)

        # Lấy nhiều sample texts hơn để tóm tắt tốt hơn
        resp = _requests_sync.get(
            f"{RAG_SERVICE_URL}/namespace/{kb.namespace}/summary",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        sample_texts = data.get("sample_texts", [])
        filenames = data.get("filenames", [])

        if not sample_texts:
            return

        # Làm sạch prefix "passage: " từ sample texts
        cleaned = [t.replace("passage: ", "").strip() for t in sample_texts]
        context = "\n\n".join(cleaned[:6])  # tối đa 6 đoạn

        # Gọi LLM tóm tắt
        import ollama
        prompt = (
            f"Dựa vào các đoạn trích sau từ kho tri thức '{kb.name}', "
            f"hãy viết một đoạn mô tả ngắn gọn (2-3 câu) về nội dung của kho tri thức này. "
            f"Chỉ trả về đoạn mô tả, không giải thích thêm.\n\n"
            f"Các đoạn trích:\n{context}"
        )
        response = ollama.chat(
            model="qwen2.5:1.5b",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1, "num_predict": 200},
        )
        summary = response["message"]["content"].strip()

        if summary:
            kb.description = summary
            kb.save(update_fields=["description"])
            import logging
            logging.getLogger(__name__).info(
                "[KB_SUMMARIZE] kb=%s summary=%s...", kb.name, summary[:80]
            )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("[KB_SUMMARIZE] kb_id=%s error=%s", kb_id, e)

@login_required
def kb_list(request):
    """Trang quản lý Knowledge Bases — chỉ admin."""
    if not request.user.is_superuser:
        messages.error(request, "Chỉ admin mới có quyền quản lý Knowledge Base.")
        return redirect('mcp_public_tools')
    from .models import KnowledgeBase, UserKnowledgeBase
    from django.db.models import Count
    kbs = KnowledgeBase.objects.all().annotate(
        user_count=Count('user_assignments', filter=Q(user_assignments__is_active=True))
    ).order_by('-is_system', 'category', 'name')
    return render(request, 'ai_hub/kb_list.html', {'kbs': kbs})


@login_required
def kb_create(request):
    if not request.user.is_superuser:
        return redirect('mcp_public_tools')
    from .models import KnowledgeBase
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        namespace = request.POST.get('namespace', '').strip()
        category = request.POST.get('category', 'General').strip()
        icon = request.POST.get('icon', 'fa-book').strip()
        is_public = request.POST.get('is_public') == 'on'
        is_system = request.POST.get('is_system') == 'on'
        if not name or not namespace:
            messages.error(request, "Tên và Namespace là bắt buộc.")
        elif KnowledgeBase.objects.filter(namespace=namespace).exists():
            messages.error(request, f"Namespace '{namespace}' đã tồn tại.")
        else:
            KnowledgeBase.objects.create(
                name=name, description=description, namespace=namespace,
                category=category, icon=icon, is_public=is_public,
                is_system=is_system, created_by=request.user,
            )
            messages.success(request, f"Đã tạo Knowledge Base '{name}'.")
            return redirect('kb_list')
    return render(request, 'ai_hub/kb_form.html', {'action': 'Tạo mới', 'kb': None})


@login_required
def kb_edit(request, kb_id):
    if not request.user.is_superuser:
        return redirect('mcp_public_tools')
    from .models import KnowledgeBase
    kb = get_object_or_404(KnowledgeBase, id=kb_id)
    if request.method == 'POST':
        kb.name = request.POST.get('name', kb.name).strip()
        kb.description = request.POST.get('description', kb.description).strip()
        kb.category = request.POST.get('category', kb.category).strip()
        kb.icon = request.POST.get('icon', kb.icon).strip()
        kb.is_public = request.POST.get('is_public') == 'on'
        kb.is_system = request.POST.get('is_system') == 'on'
        kb.save()
        messages.success(request, f"Đã cập nhật '{kb.name}'.")
        return redirect('kb_list')
    return render(request, 'ai_hub/kb_form.html', {'action': 'Chỉnh sửa', 'kb': kb})


@login_required
@require_http_methods(["POST"])
def kb_delete(request, kb_id):
    if not request.user.is_superuser:
        return redirect('mcp_public_tools')
    from .models import KnowledgeBase
    kb = get_object_or_404(KnowledgeBase, id=kb_id)
    name = kb.name
    kb.delete()
    messages.success(request, f"Đã xóa '{name}'.")
    return redirect('kb_list')


@login_required
@require_http_methods(["POST"])
def kb_upload_document(request, kb_id):
    """Upload tài liệu vào namespace của KB (admin only)."""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    from .models import KnowledgeBase
    from pathlib import Path
    kb = get_object_or_404(KnowledgeBase, id=kb_id)
    file = request.FILES.get('file')
    if not file:
        return JsonResponse({'success': False, 'error': 'Thiếu file'}, status=400)
    ext = Path(file.name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return JsonResponse({'success': False, 'error': f'Định dạng không hỗ trợ: {ext}'}, status=400)
    if file.size > MAX_UPLOAD_SIZE:
        return JsonResponse({'success': False, 'error': 'File quá lớn (tối đa 20MB)'}, status=400)
    file_content = file.read()
    try:
        resp = _requests_sync.post(
            f"{RAG_SERVICE_URL}/upload",
            files={'file': (file.name, file_content, file.content_type or 'application/octet-stream')},
            data={'namespace': kb.namespace},
            timeout=180,  # 3 phút — lần đầu load embedding model mất thời gian
        )
        resp.raise_for_status()
        result = resp.json()
        chunks = result.get('chunks_indexed', result.get('chunks_added', 0))
        if result.get('status') == 'skipped':
            # File đã tồn tại, không thay đổi
            return JsonResponse({'success': True, 'chunks': 0, 'namespace': kb.namespace,
                                 'filename': file.name, 'skipped': True})
        if chunks == 0:
            return JsonResponse({'success': False, 'error': 'RAG service không index được nội dung (0 chunks). File có thể rỗng hoặc không đọc được.'}, status=422)

        # Tự động tóm tắt KB trong background sau khi upload
        import threading
        threading.Thread(
            target=_auto_summarize_kb,
            args=(kb.id,),
            daemon=True,
            name=f"kb-summarize-{kb.id}",
        ).start()

        return JsonResponse({'success': True, 'chunks': chunks, 'namespace': kb.namespace, 'filename': file.name})
    except _requests_sync.exceptions.ConnectionError:
        return JsonResponse({'success': False, 'error': 'RAG service chưa khởi động'}, status=503)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def kb_documents(request, kb_id):
    """Lấy danh sách tài liệu trong namespace của KB từ RAG service."""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    from .models import KnowledgeBase
    kb = get_object_or_404(KnowledgeBase, id=kb_id)
    try:
        resp = _requests_sync.get(
            f"{RAG_SERVICE_URL}/namespace/{kb.namespace}/summary",
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        docs = data.get('filenames', data.get('documents', []))
        return JsonResponse({'success': True, 'namespace': kb.namespace, 'documents': docs})
    except _requests_sync.exceptions.ConnectionError:
        return JsonResponse({'success': False, 'error': 'RAG service chưa khởi động'}, status=503)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def kb_info(request, kb_id):
    """Trả về thông tin KB bao gồm description hiện tại (dùng để poll sau auto-summarize)."""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    from .models import KnowledgeBase
    kb = get_object_or_404(KnowledgeBase, id=kb_id)
    return JsonResponse({'success': True, 'id': kb.id, 'description': kb.description or ''})


@login_required
@require_http_methods(["POST"])
def kb_delete_document(request, kb_id):
    """Xóa một file cụ thể trong namespace của KB."""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    from .models import KnowledgeBase
    kb = get_object_or_404(KnowledgeBase, id=kb_id)
    filename = request.POST.get('filename', '').strip()
    if not filename:
        return JsonResponse({'success': False, 'error': 'Thiếu tên file'}, status=400)
    try:
        resp = _requests_sync.delete(
            f"{RAG_SERVICE_URL}/namespace/{kb.namespace}/file/{filename}",
            timeout=15,
        )
        resp.raise_for_status()
        return JsonResponse({'success': True})
    except _requests_sync.exceptions.ConnectionError:
        return JsonResponse({'success': False, 'error': 'RAG service chưa khởi động'}, status=503)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def kb_clear_namespace(request, kb_id):
    """Xóa toàn bộ namespace trên RAG service."""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    from .models import KnowledgeBase
    kb = get_object_or_404(KnowledgeBase, id=kb_id)
    try:
        resp = _requests_sync.delete(
            f"{RAG_SERVICE_URL}/namespace/{kb.namespace}",
            timeout=10,
        )
        resp.raise_for_status()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
