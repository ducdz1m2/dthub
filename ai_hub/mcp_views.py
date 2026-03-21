"""
MCP Server Management Views for DTHub AI Hub
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import json
import logging
import asyncio
from .models import MCPServer as MCPServerModel
from .mcp_client import get_mcp_client, MCPServer, MCPDiscoveryClient
import subprocess
import tempfile
import os
import time
import signal
import requests

logger = logging.getLogger(__name__)

import ipaddress
import urllib.parse

def _is_safe_endpoint(url: str) -> bool:
    """
    SSRF protection: chặn các URL trỏ vào metadata cloud, loopback, link-local.
    Chỉ cho phép http/https. localhost và 127.x được phép (local MCP servers).
    """
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return False
        host = parsed.hostname or ''
        # Chặn cloud metadata endpoints
        blocked_hosts = ['169.254.169.254', 'metadata.google.internal']
        if host in blocked_hosts:
            return False
        # Chặn các dải IP nội bộ nguy hiểm (trừ localhost)
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_link_local or ip.is_multicast:
                return False
            # Cho phép loopback (localhost MCP servers)
        except ValueError:
            pass  # hostname, không phải IP — OK
        return True
    except Exception:
        return False

@login_required
def mcp_server_editor(request, pk):
    """Trình soạn thảo mã nguồn MCP Server (FastAPI)"""
    if not request.user.is_superuser:
        return redirect('mcp_public_tools')
    
    server = get_object_or_404(MCPServerModel, pk=pk)
    
    # Template mặc định nếu chưa có code
    if not server.code_template:
        try:
            template_path = os.path.join(os.path.dirname(__file__), 'mcp_server_template.py')
            with open(template_path, 'r', encoding='utf-8') as f:
                server.code_template = f.read()
        except:
            server.code_template = "# Viết code FastAPI của bạn ở đây..."

    context = {
        'server': server,
    }
    return render(request, 'ai_hub/mcp_server_editor.html', context)

@require_http_methods(["POST"])
@login_required
def mcp_save_code(request, pk):
    """Lưu mã nguồn MCP Server"""
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
    
    server = get_object_or_404(MCPServerModel, pk=pk)
    try:
        data = json.loads(request.body)
        server.code_template = data.get('code', '')
        server.save()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def mcp_test_code(request, pk):
    """Chạy thử mã nguồn MCP Server trong một tiến trình tạm thời"""
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)
        
    server = get_object_or_404(MCPServerModel, pk=pk)
    code = server.code_template
    
    # Tạo file tạm để chạy
    with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False, encoding='utf-8') as tmp:
        tmp.write(code)
        tmp_path = tmp.name
        
    try:
        # 1. Khởi chạy server tạm thời trên port ngẫu nhiên (ví dụ 8002)
        test_port = 8002
        process = subprocess.Popen(
            ['python', tmp_path],
            env={**os.environ, 'PORT': str(test_port)},
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # Đợi server khởi động
        time.sleep(3)
        
        # 2. Thử gọi /metadata để kiểm tra tool schema
        logs = []
        try:
            test_url = f"http://localhost:{test_port}"
            headers = {'X-Token': server.auth_token}
            
            resp = requests.get(f"{test_url}/metadata", headers=headers, timeout=5)
            logs.append(f"> GET /metadata: HTTP {resp.status_code}")
            if resp.status_code == 200:
                logs.append(f"> Tools found: {json.dumps(resp.json().get('tools', []), indent=2, ensure_ascii=False)}")
                
                # Cập nhật tools vào DB luôn nếu test thành công
                # server.endpoint = test_url # Không cập nhật endpoint thật
                # discovery = MCPDiscoveryClient.discover_tools(server.id)
            else:
                logs.append(f"> Error Response: {resp.text}")
        except Exception as e:
            logs.append(f"> Connection Error: {str(e)}")
            
        # 3. Dừng server
        process.terminate()
        try:
            process.wait(timeout=5)
        except:
            process.kill()
            
        # Thu thập nốt logs từ stdout
        remaining_logs, _ = process.communicate()
        full_logs = "\n".join(logs) + "\n\n--- SERVER STDOUT ---\n" + remaining_logs
        
        server.last_test_log = full_logs
        server.save()
        
        os.unlink(tmp_path)
        
        return JsonResponse({
            'status': 'success', 
            'logs': full_logs,
            'is_valid': "GET /metadata: HTTP 200" in full_logs
        })
        
    except Exception as e:
        if os.path.exists(tmp_path): os.unlink(tmp_path)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def mcp_sync_tools(request, pk):
    """Đồng bộ hóa tools từ MCP Server URL"""
    if not request.user.is_superuser:
        return redirect('mcp_public_tools')
        
    result = MCPDiscoveryClient.discover_tools(pk)
    if result['status'] == 'success':
        pass
    
    return redirect('mcp_server_detail', device_id=get_object_or_404(MCPServerModel, pk=pk).device_id)

@require_http_methods(["POST"])
@login_required
def mcp_sync_by_device_id(request, device_id):
    """Sync tools từ MCP Server theo device_id — dùng cho nút Đồng bộ tổng."""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Forbidden'}, status=403)
    try:
        server = MCPServerModel.objects.get(device_id=device_id, is_active=True)
        result = MCPDiscoveryClient.discover_tools(server.pk)
        return JsonResponse(result)
    except MCPServerModel.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Server không tồn tại'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def mcp_dashboard(request):
    """MCP Server Dashboard - Chỉ Superuser mới được phép quản lý"""
    if not request.user.is_superuser:
        return redirect('mcp_public_tools')

    try:
        db_servers = MCPServerModel.objects.all().order_by('name')
        mcp_client = get_mcp_client()

        # Nếu cache rỗng (vừa restart), auto-discover từ DB rồi refresh tools trong background
        if not mcp_client.servers:
            try:
                new_ids = mcp_client.discover_servers()
                if new_ids:
                    import threading
                    def _bg_refresh():
                        for did in new_ids:
                            try:
                                mcp_client.refresh_server_capabilities(did)
                            except Exception:
                                pass
                    threading.Thread(target=_bg_refresh, daemon=True).start()
            except Exception as e:
                logger.warning(f"Auto-discover failed: {e}")

        all_servers = []
        for db_server in db_servers:
            cached = mcp_client.servers.get(db_server.device_id)
            if cached:
                cached.db_is_active = db_server.is_active
                all_servers.append(cached)
            else:
                s = MCPServer(db_server.device_id, db_server.get_endpoint or "", db_server.auth_token)
                s.is_online = False
                s.db_is_active = db_server.is_active
                all_servers.append(s)

        online_servers = [s for s in all_servers if s.is_online]
        all_tools = {s.device_id: s.tools for s in all_servers}
        all_resources = {s.device_id: s.resources for s in all_servers}

        context = {
            'servers': all_servers,
            'online_servers': online_servers,
            'resources': all_resources,
            'tools': all_tools,
            'discovered_count': 0,
            'total_count': len(all_servers),
            'online_count': len(online_servers),
            'total_tools_count': sum(len(t) for t in all_tools.values()),
            'total_resources_count': sum(len(r) for r in all_resources.values()),
        }

    except Exception as e:
        logger.error(f"Error loading MCP dashboard: {e}")
        context = {
            'servers': [], 'online_servers': [], 'resources': {}, 'tools': {},
            'discovered_count': 0, 'total_count': 0, 'online_count': 0,
            'total_tools_count': 0, 'total_resources_count': 0,
        }

    return render(request, 'ai_hub/mcp_dashboard.html', context)

@login_required
def mcp_server_detail(request, device_id):
    """MCP Server Detail View - Superuser Only"""
    if not request.user.is_superuser:
        return redirect('mcp_public_tools')

    mcp_client = get_mcp_client()
    server = mcp_client.get_server(device_id)

    if not server:
        # Tạo từ DB, không test connection
        db_server = MCPServerModel.objects.filter(device_id=device_id).first()
        if not db_server:
            return JsonResponse({'error': 'Server not found'}, status=404)
        server = MCPServer(db_server.device_id, db_server.get_endpoint or "", db_server.auth_token)
        server.is_online = False
        mcp_client.servers[device_id] = server

    server_model = MCPServerModel.objects.filter(device_id=device_id).first()

    context = {
        'server': server,
        'server_model': server_model,
        'resources': server.resources,
        'tools': server.tools,
        'capabilities': server.capabilities,
    }

    if request.GET.get('partial') == '1':
        return render(request, 'ai_hub/mcp_server_detail_partial.html', context)

    return render(request, 'ai_hub/mcp_server_detail.html', context)

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def mcp_register_server(request):
    """Register a new MCP server - Superuser Only"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Forbidden'}, status=403)
        
    try:
        data = json.loads(request.body)
        device_id = data.get('device_id')
        endpoint = data.get('endpoint')
        auth_token = data.get('auth_token')
        
        if not device_id or not endpoint:
            return JsonResponse({'error': 'device_id and endpoint are required'}, status=400)
        
        mcp_client = get_mcp_client()
        success = mcp_client.register_server_endpoint(device_id, endpoint, auth_token, test_connection=True)
        
        if success:
            return JsonResponse({
                'status': 'success',
                'message': f'MCP server {device_id} registered successfully'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': f'Failed to register MCP server {device_id}'
            }, status=400)
            
    except Exception as e:
        logger.error(f"Error registering MCP server: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def mcp_unregister_server(request, device_id):
    """Unregister an MCP server - Superuser Only"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Forbidden'}, status=403)
        
    try:
        mcp_client = get_mcp_client()
        mcp_client.unregister_server(device_id)

        server_obj = MCPServerModel.objects.filter(device_id=device_id).first()
        if server_obj:
            server_obj.delete()
        
        return JsonResponse({
            'status': 'success',
            'message': f'MCP server {device_id} unregistered successfully'
        })
        
    except Exception as e:
        logger.error(f"Error unregistering MCP server {device_id}: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def mcp_call_tool(request, device_id):
    """Call a tool on an MCP server — login required, superuser hoặc owner của server"""
    if not request.user.is_superuser:
        # Non-superuser chỉ được gọi tool trên server public hoặc server của chính họ
        server_obj = MCPServerModel.objects.filter(device_id=device_id, is_active=True).first()
        if not server_obj:
            return JsonResponse({'error': 'Server not found'}, status=404)
        if not server_obj.is_public and server_obj.owner != request.user:
            return JsonResponse({'error': 'Forbidden'}, status=403)
    try:
        data = json.loads(request.body)
        tool_name = data.get('tool_name')
        arguments = data.get('arguments', {})
        use_mqtt = data.get('use_mqtt', False)
        
        if not tool_name:
            return JsonResponse({'error': 'tool_name is required'}, status=400)
        
        mcp_client = get_mcp_client()
        
        if use_mqtt:
            return JsonResponse({
                'status': 'error',
                'message': 'MQTT is no longer supported. Use HTTP only.'
            }, status=400)
        else:
            result = mcp_client.call_tool(device_id, tool_name, arguments)

        if isinstance(result, dict):
            if result.get('error'):
                return JsonResponse(
                    {
                        'status': 'error',
                        'message': result.get('error'),
                        'result': result,
                        'device_id': device_id,
                        'tool_name': tool_name,
                        'use_mqtt': use_mqtt
                    },
                    status=400
                )
            if result.get('success') is False:
                return JsonResponse(
                    {
                        'status': 'error',
                        'message': 'Tool execution failed',
                        'result': result,
                        'device_id': device_id,
                        'tool_name': tool_name,
                        'use_mqtt': use_mqtt
                    },
                    status=400
                )

        return JsonResponse(
            {
                'status': 'success',
                'result': result,
                'device_id': device_id,
                'tool_name': tool_name,
                'use_mqtt': use_mqtt
            }
        )
        
    except Exception as e:
        logger.error(f"Error calling tool on MCP server {device_id}: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def mcp_refresh_server(request, device_id):
    """Refresh MCP server capabilities - Superuser Only"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Forbidden'}, status=403)
        
    try:
        mcp_client = get_mcp_client()
        if not mcp_client.get_server(device_id):
            mcp_client.discover_servers()
        success = mcp_client.refresh_server_capabilities(device_id)
        
        if success:
            server = mcp_client.get_server(device_id)
            return JsonResponse({
                'status': 'success',
                'message': f'MCP server {device_id} refreshed successfully',
                'server': {
                    'device_id': server.device_id,
                    'is_online': server.is_online,
                    'last_seen': server.last_seen.isoformat() if server.last_seen else None,
                    'resources_count': len(server.resources),
                    'tools_count': len(server.tools)
                }
            })
        else:
            server = mcp_client.get_server(device_id)
            error_message = None
            if server and getattr(server, "last_error", None):
                error_message = server.last_error
            return JsonResponse({
                'status': 'error',
                'message': error_message or f'Failed to refresh MCP server {device_id}'
            }, status=400)
            
    except Exception as e:
        logger.error(f"Error refreshing MCP server {device_id}: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@login_required
def mcp_health_check(request):
    """Perform health check on all MCP servers - Superuser Only"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Forbidden'}, status=403)
        
    try:
        mcp_client = get_mcp_client()
        health_status = mcp_client.health_check()
        
        return JsonResponse({
            'status': 'success',
            'health_check': health_status,
            'timestamp': timezone.now().isoformat(),
            'summary': {
                'total_servers': len(health_status),
                'online_servers': sum(1 for status in health_status.values() if status),
                'offline_servers': sum(1 for status in health_status.values() if not status)
            }
        })
        
    except Exception as e:
        logger.error(f"Error performing MCP health check: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def mcp_toggle_server(request, device_id):
    """Toggle is_active cho MCP server — Superuser Only"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Forbidden'}, status=403)
    try:
        server = get_object_or_404(MCPServerModel, device_id=device_id)
        server.is_active = not server.is_active
        server.save(update_fields=['is_active'])

        # Nếu disable: xóa khỏi cache client
        if not server.is_active:
            mcp_client = get_mcp_client()
            mcp_client.servers.pop(device_id, None)

        return JsonResponse({'status': 'success', 'is_active': server.is_active})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def mcp_discover_servers(request):
    """Quét mạng nội bộ tìm MCP server mới — chỉ chạy khi user bấm nút."""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Forbidden'}, status=403)

    try:
        from .mcp_scanner import scan_and_register
        found = scan_and_register(request.user)

        return JsonResponse({
            'status': 'success',
            'discovered_count': len(found),
            'discovered_servers': [s.device_id for s in found],
            'tools_synced': True,
            'timestamp': timezone.now().isoformat()
        })

    except Exception as e:
        logger.error("Lỗi quét MCP server: %s", e)
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def mcp_server_resources(request, device_id):
    """Get resources from a specific MCP server - Superuser Only"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Forbidden'}, status=403)
        
    try:
        mcp_client = get_mcp_client()
        server = mcp_client.get_server(device_id)
        
        if not server:
            return JsonResponse({'error': 'Server not found'}, status=404)
        
        resources = server.get_resources()
        
        return JsonResponse({
            'status': 'success',
            'device_id': device_id,
            'resources': resources,
            'resources_count': len(resources)
        })
        
    except Exception as e:
        logger.error(f"Error getting resources from MCP server {device_id}: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def mcp_server_tools(request, device_id):
    """Get tools from a specific MCP server - Superuser Only"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Forbidden'}, status=403)
        
    try:
        mcp_client = get_mcp_client()
        server = mcp_client.get_server(device_id)
        
        if not server:
            return JsonResponse({'error': 'Server not found'}, status=404)
        
        tools = server.get_tools()
        
        return JsonResponse({
            'status': 'success',
            'device_id': device_id,
            'tools': tools,
            'tools_count': len(tools)
        })
        
    except Exception as e:
        logger.error(f"Error getting tools from MCP server {device_id}: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def mcp_auto_register(request):
    """Auto-register MCP server - Superuser Only"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Forbidden'}, status=403)
        
    try:
        data = json.loads(request.body)
        device_id = data.get('device_id')
        ip_address = data.get('ip_address')
        port = data.get('port', 80)
        device_type = data.get('device_type', 'hybrid')
        name = data.get('name', f'Auto-registered {device_id}')
        firmware_version = data.get('firmware_version')
        capabilities = data.get('capabilities', {})
        
        if not device_id or not ip_address:
            return JsonResponse({'error': 'device_id and ip_address are required'}, status=400)

        # SSRF protection: chỉ cho phép endpoint hợp lệ
        endpoint = data.get('endpoint', f"http://{ip_address}:{port}")
        if not _is_safe_endpoint(endpoint):
            return JsonResponse({'error': 'Endpoint không hợp lệ hoặc bị chặn'}, status=400)
        
        # Create or update device
        device, created = ESP32Device.objects.get_or_create(
            device_id=device_id,
            defaults={
                'name': name,
                'device_type': device_type,
                'ip_address': ip_address,
                'is_active': True
            }
        )
        
        if not created:
            device.name = name
            device.device_type = device_type
            device.ip_address = ip_address
            device.is_active = True
            device.save()
        
        # Initialize MCP client with this device
        mcp_client = get_mcp_client()
        if mcp_client.register_server_endpoint(device_id, endpoint, auth_token=None, test_connection=True):
            return JsonResponse({
                'status': 'success',
                'message': f'MCP server {device_id} auto-registered successfully',
                'device_id': device_id,
                'ip_address': ip_address,
                'registered': True
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': f'Failed to register MCP server {device_id}',
                'device_id': device_id
            }, status=400)
            
    except Exception as e:
        logger.error(f"Error in auto-registration: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def mcp_batch_operation(request):
    """Perform batch operations on multiple MCP servers — superuser only"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Forbidden'}, status=403)
    try:
        data = json.loads(request.body)
        operation = data.get('operation')
        device_ids = data.get('device_ids', [])
        parameters = data.get('parameters', {})
        
        if not operation or not device_ids:
            return JsonResponse({'error': 'operation and device_ids are required'}, status=400)
        
        mcp_client = get_mcp_client()
        results = {}
        
        for device_id in device_ids:
            try:
                if operation == 'refresh':
                    success = mcp_client.refresh_server_capabilities(device_id)
                    results[device_id] = {'success': success}
                elif operation == 'health_check':
                    server = mcp_client.get_server(device_id)
                    if server:
                        info = server.get_info()
                        results[device_id] = {'success': bool(info), 'info': info}
                    else:
                        results[device_id] = {'success': False, 'error': 'Server not found'}
                elif operation == 'call_tool':
                    tool_name = parameters.get('tool_name')
                    arguments = parameters.get('arguments', {})
                    if tool_name:
                        result = mcp_client.call_tool(device_id, tool_name, arguments)
                        results[device_id] = {'success': True, 'result': result}
                    else:
                        results[device_id] = {'success': False, 'error': 'tool_name required'}
                else:
                    results[device_id] = {'success': False, 'error': f'Unknown operation: {operation}'}
                    
            except Exception as e:
                results[device_id] = {'success': False, 'error': str(e)}
        
        return JsonResponse({
            'status': 'success',
            'operation': operation,
            'results': results,
            'summary': {
                'total': len(device_ids),
                'successful': sum(1 for r in results.values() if r.get('success', False)),
                'failed': sum(1 for r in results.values() if not r.get('success', False))
            }
        })
        
    except Exception as e:
        logger.error(f"Error performing MCP batch operation: {e}")
        return JsonResponse({'error': str(e)}, status=500)
