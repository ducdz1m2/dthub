from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.contrib.auth.decorators import permission_required, login_required
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import json
from .models import ESP32Device, SensorData, DeviceCommand, ChatSession, ChatMessage
from .rag_mcp_integration import rag_mcp_service
import sys
import os

# Add rag-mcp to Python path for RAG database
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'rag-mcp'))

@permission_required("ai_hub.manage_ai_architecture", raise_exception=True)
def ai_arch_view(request):
    return HttpResponse("AI Architect only")

@login_required
def dashboard_view(request):
    """Main dashboard cho AI Hub"""
    devices = ESP32Device.objects.filter(is_active=True)
    recent_sensor_data = SensorData.objects.select_related('device').order_by('-timestamp')[:20]
    
    context = {
        'devices': devices,
        'recent_data': recent_sensor_data,
    }
    return render(request, 'ai_hub/dashboard.html', context)

@login_required
def chat_interface(request):
    """Chat interface với RAG-MCP - streaming response"""
    if request.method == 'POST':
        data = json.loads(request.body)
        query = data.get('query', '')
        
        # Tạo hoặc lấy session
        session_id = request.session.get('chat_session_id')
        if not session_id:
            # Generate unique session ID
            import uuid
            session_id = str(uuid.uuid4())
            session = ChatSession.objects.create(user=request.user, session_id=session_id)
            request.session['chat_session_id'] = session.session_id
        else:
            try:
                session = ChatSession.objects.get(session_id=session_id, user=request.user)
            except ChatSession.DoesNotExist:
                # If session doesn't exist, create new one
                import uuid
                session_id = str(uuid.uuid4())
                session = ChatSession.objects.create(user=request.user, session_id=session_id)
                request.session['chat_session_id'] = session.session_id
        
        # Process query với RAG-MCP - streaming response
        import time
        import ollama
        start_time = time.time()
        selected_tool, confidence = rag_mcp_service.dispatcher.smart_route(query)
        
        if selected_tool in rag_mcp_service.dispatcher.tools:
            handler = rag_mcp_service.dispatcher.tools[selected_tool]["handler"]
            
            if selected_tool == "rag_search":
                if rag_mcp_service.retriever:
                    prompt = handler(query, rag_mcp_service.retriever)
                else:
                    prompt = "Xin lỗi, database tìm kiếm chưa được tải. Vui lòng kiểm tra lại file FAISS index."
            else:
                prompt = handler(query)
        else:
            prompt = query
        
        # Streaming generator function
        def generate_response():
            full_response = ""
            try:
                # Debug: Send initial message
                yield f"data: {json.dumps({'debug': 'Starting ollama chat...', 'done': False})}\n\n"
                
                # Test simple response first
                if selected_tool == "general_chat":
                    # For general chat, return handler response directly without ollama
                    response = handler(query)
                    yield f"data: {json.dumps({'chunk': response, 'done': False})}\n\n"
                    yield f"data: {json.dumps({'done': True, 'full_response': response, 'tool_used': selected_tool, 'confidence': confidence, 'response_time': 0.1})}\n\n"
                else:
                    # Use ollama for other tools
                    stream = ollama.chat(
                        model="qwen2.5:1.5b",
                        messages=[{"role": "user", "content": prompt}],
                        stream=True,  # Enable streaming
                        options={
                            "temperature": 0.1,
                            "num_predict": 250
                        }
                    )
                    
                    yield f"data: {json.dumps({'debug': 'Ollama stream started...', 'done': False})}\n\n"
                    
                    chunk_count = 0
                    for chunk in stream:
                        content = chunk['message']['content']
                        full_response += content
                        chunk_count += 1
                        # Send chunk as SSE format with immediate flush
                        chunk_data = f"data: {json.dumps({'chunk': content, 'done': False, 'chunk_num': chunk_count})}\n\n"
                        yield chunk_data
                        # Minimal delay to allow browser processing
                        if chunk_count % 5 == 0:  # Only pause every 5 chunks
                            import time
                            time.sleep(0.001)
                    
                    yield f"data: {json.dumps({'debug': f'Stream completed with {chunk_count} chunks', 'done': False})}\n\n"
                    
                    # Send completion signal
                    response_time = time.time() - start_time
                    yield f"data: {json.dumps({'done': True, 'full_response': full_response, 'tool_used': selected_tool, 'confidence': confidence, 'response_time': response_time})}\n\n"
                
                # Lưu message sau khi hoàn thành
                if selected_tool == "general_chat":
                    ChatMessage.objects.create(
                        session=session,
                        query=query,
                        response=response,
                        tool_used=selected_tool,
                        confidence=confidence,
                        response_time=0.1
                    )
                else:
                    ChatMessage.objects.create(
                        session=session,
                        query=query,
                        response=full_response,
                        tool_used=selected_tool,
                        confidence=confidence,
                        response_time=response_time
                    )
                
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                yield f"data: {json.dumps({'error': f'Lỗi khi gọi LLM: {str(e)}', 'debug': error_details, 'done': True})}\n\n"
        
        # Return streaming response
        response = StreamingHttpResponse(
            generate_response(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['Connection'] = 'keep-alive'
        response['X-Accel-Buffering'] = 'no'
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    return render(request, 'ai_hub/chat.html')

@login_required
def device_management(request):
    """Quản lý ESP32 devices"""
    devices = ESP32Device.objects.all()
    
    if request.method == 'POST':
        data = json.loads(request.body)
        device_id = data.get('device_id')
        
        if device_id:
            device = get_object_or_404(ESP32Device, device_id=device_id)
            device.name = data.get('name', device.name)
            device.location = data.get('location', device.location)
            device.is_active = data.get('is_active', device.is_active)
            device.save()
            
            return JsonResponse({'status': 'success', 'device': device.name})
    
    return render(request, 'ai_hub/devices.html', {'devices': devices})

@login_required
def sensor_data_view(request, device_id=None):
    """View sensor data"""
    if device_id:
        device = get_object_or_404(ESP32Device, device_id=device_id)
        sensor_data = SensorData.objects.filter(device=device).order_by('-timestamp')[:100]
    else:
        device = None
        sensor_data = SensorData.objects.select_related('device').order_by('-timestamp')[:100]
    
    return render(request, 'ai_hub/sensor_data.html', {
        'device': device,
        'sensor_data': sensor_data
    })

@csrf_exempt
@require_http_methods(["POST"])
def mqtt_webhook(request):
    """Webhook để nhận data từ MQTT broker"""
    try:
        data = json.loads(request.body)
        topic = data.get('topic', '')
        payload = data.get('payload', {})
        
        # Parse topic: esp32/device_id/message_type
        topic_parts = topic.split('/')
        if len(topic_parts) >= 3 and topic_parts[0] == 'esp32':
            device_id = topic_parts[1]
            message_type = topic_parts[2]
            
            device, created = ESP32Device.objects.get_or_create(
                device_id=device_id,
                defaults={'name': f'ESP32 {device_id}', 'mqtt_topic': topic}
            )
            
            if message_type == 'sensor_data':
                # Lưu sensor data
                for sensor_type, value in payload.items():
                    if isinstance(value, (int, float)):
                        SensorData.objects.create(
                            device=device,
                            sensor_type=sensor_type,
                            value=value,
                            unit=get_sensor_unit(sensor_type)
                        )
                
                # Update last_seen
                device.last_seen = timezone.now()
                device.save()
                
                return JsonResponse({'status': 'success', 'message': 'Sensor data saved'})
        
        return JsonResponse({'status': 'error', 'message': 'Invalid topic'}, status=400)
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def get_sensor_unit(sensor_type):
    """Get unit cho sensor type"""
    units = {
        'temperature': '°C',
        'humidity': '%',
        'light': 'lux',
        'motion': '',
        'soil_moisture': '%',
        'ph': 'pH'
    }
    return units.get(sensor_type, '')

@login_required
def send_device_command(request, device_id):
    """Gửi command đến ESP32 device"""
    if request.method == 'POST':
        device = get_object_or_404(ESP32Device, device_id=device_id)
        data = json.loads(request.body)
        
        command = data.get('command')
        parameters = data.get('parameters', {})
        
        # Tạo command record
        device_command = DeviceCommand.objects.create(
            device=device,
            command=command,
            parameters=parameters
        )
        
        # Gửi qua MQTT
        if rag_mcp_service.mqtt_client:
            topic = f"esp32/{device_id}/commands"
            payload = {
                'command': command,
                'parameters': parameters,
                'command_id': device_command.id
            }
            rag_mcp_service.mqtt_client.publish(topic, json.dumps(payload))
            device_command.status = 'sent'
            device_command.save()
        
        return JsonResponse({
            'status': 'success',
            'command_id': device_command.id,
            'command': command
        })
    
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)
