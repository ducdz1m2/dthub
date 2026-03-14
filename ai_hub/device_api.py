"""
HTTP API Views for ESP8266 Device Communication with Ngrok Integration
Replaces MQTT communication with HTTP + Token Authentication + Ngrok Tunnels
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import json
import logging
from .models import MCPServer as MCPServerModel
from .utils.ngrok_manager import ngrok_manager
from .mcp_client import get_mcp_client

logger = logging.getLogger(__name__)

def get_device_from_token(request):
    """Extract token from request and authenticate device"""
    # Try to get token from Authorization header first
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]  # Remove 'Bearer ' prefix
    else:
        # Fall back to POST parameter
        token = request.POST.get('token') or request.GET.get('token')
    
    if not token:
        return None, JsonResponse({'error': 'Authentication token required'}, status=401)
    
    server = MCPServerModel.objects.filter(auth_token=token, is_active=True).first()
    if not server:
        return None, JsonResponse({'error': 'Invalid or expired token'}, status=401)
    
    return server, None

@csrf_exempt
@require_http_methods(["POST"])
def mcp_device_register(request):
    """Register MCP device and create ngrok tunnel"""
    try:
        data = json.loads(request.body)
        device_id = data.get('device_id')
        local_ip = data.get('local_ip')
        local_port = data.get('local_port', 80)
        name = data.get('name', f'ESP8266 {device_id}')
        server_type = data.get('server_type', 'private')
        capabilities = data.get('capabilities', {})
        
        if not device_id or not local_ip:
            return JsonResponse({'error': 'device_id and local_ip are required'}, status=400)
        
        # Create or update MCP server record
        server, created = MCPServerModel.objects.get_or_create(
            device_id=device_id,
            defaults={
                'name': name,
                'server_type': server_type,
                'connection_method': 'http',
                'description': f'Auto-registered ESP8266 device',
                'is_active': True
            }
        )
        
        if not created:
            server.name = name
            server.is_active = True
            server.last_seen = timezone.now()
            server.save()
        
        # Register with MCP client (creates ngrok tunnel)
        mcp_client = get_mcp_client()
        success = mcp_client.register_server(device_id, local_ip, local_port, server.auth_token)
        
        if success:
            # Get the public URL from ngrok manager
            public_url = ngrok_manager.get_device_url(device_id)
            
            return JsonResponse({
                'status': 'success',
                'message': f'MCP device {device_id} registered successfully',
                'device_id': device_id,
                'auth_token': server.auth_token,
                'public_url': public_url,
                'name': server.name,
                'registered': True,
                'timestamp': timezone.now().isoformat()
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': f'Failed to create ngrok tunnel for {device_id}'
            }, status=500)
        
    except Exception as e:
        logger.error(f"Error in MCP device registration: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def device_sensor_data(request):
    """Receive sensor data from device"""
    try:
        # Authenticate device
        device, error_response = get_device_from_token(request)
        if error_response:
            return error_response
        
        # Parse sensor data
        data = json.loads(request.body)
        timestamp = data.get('timestamp', timezone.now().isoformat())
        
        # Update device last seen
        device.last_seen = timezone.now()
        device.ip_address = request.META.get('REMOTE_ADDR', device.ip_address)
        device.save()
        
        # Process sensor readings
        sensor_readings = []
        
        # Temperature
        if 'temperature' in data:
            SensorData.objects.create(
                device=device,
                sensor_type='temperature',
                value=data['temperature'],
                unit='°C',
                timestamp=timestamp
            )
            sensor_readings.append({'type': 'temperature', 'value': data['temperature'], 'unit': '°C'})
        
        # Humidity
        if 'humidity' in data:
            SensorData.objects.create(
                device=device,
                sensor_type='humidity',
                value=data['humidity'],
                unit='%',
                timestamp=timestamp
            )
            sensor_readings.append({'type': 'humidity', 'value': data['humidity'], 'unit': '%'})
        
        # Other sensors can be added here
        
        logger.info(f"Received sensor data from {device.device_id}: {sensor_readings}")
        
        return JsonResponse({
            'status': 'success',
            'message': 'Sensor data received',
            'device_id': device.device_id,
            'readings_count': len(sensor_readings),
            'timestamp': timezone.now().isoformat()
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error processing sensor data: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def device_status(request):
    """Receive device status update"""
    try:
        # Authenticate device
        device, error_response = get_device_from_token(request)
        if error_response:
            return error_response
        
        # Parse status data
        data = json.loads(request.body)
        
        # Update device status
        device.last_seen = timezone.now()
        device.ip_address = data.get('ip_address', request.META.get('REMOTE_ADDR', device.ip_address))
        device.save()
        
        # Store status as sensor data for tracking
        status_data = {
            'relay1_state': data.get('relay1_state', False),
            'relay2_state': data.get('relay2_state', False),
            'system_active': data.get('system_active', True),
            'led_state': data.get('led_state', False),
            'free_heap': data.get('free_heap', 0),
            'uptime': data.get('uptime', 0),
            'rssi': data.get('rssi', 0)
        }
        
        # Store system status as a special sensor reading
        SensorData.objects.create(
            device=device,
            sensor_type='system_status',
            value=1,  # Placeholder value
            unit='status',
            timestamp=data.get('timestamp', timezone.now().isoformat())
        )
        
        logger.info(f"Status update from {device.device_id}: {status_data}")
        
        return JsonResponse({
            'status': 'success',
            'message': 'Status update received',
            'device_id': device.device_id,
            'timestamp': timezone.now().isoformat()
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error processing status update: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def mcp_device_heartbeat(request):
    """Receive heartbeat from MCP device"""
    try:
        # Authenticate device
        server, error_response = get_device_from_token(request)
        if error_response:
            return error_response
        
        # Parse heartbeat data
        data = json.loads(request.body)
        new_local_ip = data.get('local_ip')
        new_local_port = data.get('local_port', 80)
        
        # Update server last seen
        server.last_seen = timezone.now()
        server.save()
        
        # If IP changed, update ngrok tunnel
        if new_local_ip:
            mcp_client = get_mcp_client()
            current_url = ngrok_manager.get_device_url(server.device_id)
            
            # Update tunnel target if needed
            updated_url = ngrok_manager.update_tunnel_target(
                server.device_id, 
                new_local_ip, 
                new_local_port
            )
            
            if updated_url and updated_url != current_url:
                logger.info(f"Updated tunnel for {server.device_id}: {updated_url}")
        
        return JsonResponse({
            'status': 'success',
            'message': 'Heartbeat received',
            'device_id': server.device_id,
            'public_url': ngrok_manager.get_device_url(server.device_id),
            'timestamp': timezone.now().isoformat()
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error processing heartbeat: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET", "POST"])
def device_commands(request):
    """Send commands to device (polling endpoint)"""
    try:
        # Authenticate device
        device, error_response = get_device_from_token(request)
        if error_response:
            return error_response
        
        # Get pending commands for this device
        pending_commands = DeviceCommand.objects.filter(
            device=device,
            status='pending'
        ).order_by('created_at')
        
        commands_data = []
        for cmd in pending_commands:
            commands_data.append({
                'id': cmd.id,
                'command': cmd.command,
                'parameters': cmd.parameters,
                'created_at': cmd.created_at.isoformat()
            })
            
            # Mark as sent
            cmd.status = 'sent'
            cmd.save()
        
        return JsonResponse({
            'status': 'success',
            'device_id': device.device_id,
            'commands': commands_data,
            'commands_count': len(commands_data),
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting commands for device: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def device_command_result(request):
    """Receive command execution result from device"""
    try:
        # Authenticate device
        device, error_response = get_device_from_token(request)
        if error_response:
            return error_response
        
        # Parse command result
        data = json.loads(request.body)
        command_id = data.get('command_id')
        status = data.get('status')  # 'executed' or 'failed'
        result_message = data.get('message', '')
        
        if not command_id:
            return JsonResponse({'error': 'command_id is required'}, status=400)
        
        # Update command status
        try:
            command = DeviceCommand.objects.get(id=command_id, device=device)
            command.status = status
            command.executed_at = timezone.now()
            
            # Store result message in parameters
            if result_message:
                command.parameters['result_message'] = result_message
                command.parameters['executed_at'] = timezone.now().isoformat()
            
            command.save()
            
            logger.info(f"Command {command_id} for {device.device_id}: {status} - {result_message}")
            
            return JsonResponse({
                'status': 'success',
                'message': 'Command result recorded',
                'command_id': command_id,
                'timestamp': timezone.now().isoformat()
            })
            
        except DeviceCommand.DoesNotExist:
            return JsonResponse({'error': 'Command not found'}, status=404)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error processing command result: {e}")
        return JsonResponse({'error': str(e)}, status=500)
