from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from .models import FirmwareFile, FlashingSession
from .forms import FirmwareFileForm

def is_admin(user):
    return user.is_superuser or user.is_staff

def firmware_home(request):
    """Trang chủ firmware - hiển thị danh sách firmware có sẵn"""
    firmwares = FirmwareFile.objects.filter(is_active=True).order_by('-created_at')
    
    return render(request, 'firmware/home.html', {
        'firmwares': firmwares
    })

def firmware_detail(request, firmware_id):
    """Chi tiết firmware và trang nạp firmware"""
    firmware = get_object_or_404(FirmwareFile, id=firmware_id, is_active=True)
    
    return render(request, 'firmware/detail.html', {
        'firmware': firmware
    })

@csrf_exempt
@require_POST
def log_flashing_session(request, firmware_id):
    """Ghi log session nạp firmware"""
    try:
        firmware = get_object_or_404(FirmwareFile, id=firmware_id)
        
        # Lấy thông tin từ request
        success = request.POST.get('success', 'false').lower() == 'true'
        error_message = request.POST.get('error_message', '')
        
        # Tạo session record
        session = FlashingSession.objects.create(
            firmware=firmware,
            user_ip=request.META.get('REMOTE_ADDR', '0.0.0.0'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            success=success,
            error_message=error_message
        )
        
        return JsonResponse({
            'status': 'success',
            'session_id': session.id
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

def get_manifest(request, firmware_id):
    """Trả về file manifest.json cho ESP Web Tools"""
    firmware = get_object_or_404(FirmwareFile, id=firmware_id, is_active=True)
    
    # Đọc manifest file và trả về
    if firmware.manifest_file:
        response = HttpResponse(firmware.manifest_file.read(), content_type='application/json')
        response['Content-Disposition'] = f'inline; filename="{firmware.manifest_file.name.split("/")[-1]}"'
        return response
    else:
        # Tạo manifest mặc định nếu chưa có
        manifest = {
            "name": firmware.name,
            "version": firmware.version,
            "new_install_prompt": True,
            "builds": [
                {
                    "chipFamily": firmware.device_type,
                    "parts": [
                        {
                            "path": firmware.bin_file.url,
                            "offset": "0x0"
                        }
                    ]
                }
            ]
        }
        
        import json
        return JsonResponse(manifest)

# === Admin Management Views ===

@login_required
@user_passes_test(is_admin)
def firmware_manage(request):
    """Trang quản lý firmware cho admin"""
    firmwares = FirmwareFile.objects.all().order_by('-created_at')
    
    return render(request, 'firmware/manage.html', {
        'firmwares': firmwares
    })

@login_required
@user_passes_test(is_admin)
def firmware_create(request):
    """Tạo firmware mới"""
    if request.method == 'POST':
        form = FirmwareFileForm(request.POST, request.FILES)
        if form.is_valid():
            firmware = form.save()
            messages.success(request, f"Firmware '{firmware.name}' đã được tạo thành công!")
            return redirect('firmware_manage')
        else:
            messages.error(request, "Có lỗi xảy ra. Vui lòng kiểm tra lại thông tin.")
    else:
        form = FirmwareFileForm()
    
    return render(request, 'firmware/create.html', {
        'form': form
    })

@login_required
@user_passes_test(is_admin)
def firmware_edit(request, firmware_id):
    """Chỉnh sửa firmware"""
    firmware = get_object_or_404(FirmwareFile, id=firmware_id)
    
    if request.method == 'POST':
        form = FirmwareFileForm(request.POST, request.FILES, instance=firmware)
        if form.is_valid():
            firmware = form.save()
            messages.success(request, f"Firmware '{firmware.name}' đã được cập nhật thành công!")
            return redirect('firmware_manage')
        else:
            messages.error(request, "Có lỗi xảy ra. Vui lòng kiểm tra lại thông tin.")
    else:
        form = FirmwareFileForm(instance=firmware)
    
    return render(request, 'firmware/edit.html', {
        'form': form,
        'firmware': firmware
    })

@login_required
@user_passes_test(is_admin)
def firmware_delete(request, firmware_id):
    """Xóa firmware"""
    firmware = get_object_or_404(FirmwareFile, id=firmware_id)
    
    if request.method == 'POST':
        firmware_name = firmware.name
        firmware.delete()
        messages.success(request, f"Firmware '{firmware_name}' đã được xóa thành công!")
        return redirect('firmware_manage')
    
    return render(request, 'firmware/delete_confirm.html', {
        'firmware': firmware
    })

@login_required
@user_passes_test(is_admin)
def firmware_stats(request):
    """Thống kê firmware"""
    total_firmwares = FirmwareFile.objects.count()
    active_firmwares = FirmwareFile.objects.filter(is_active=True).count()
    total_flashes = FlashingSession.objects.count()
    successful_flashes = FlashingSession.objects.filter(success=True).count()
    
    # Firmware theo device type với phần trăm
    firmware_by_device = []
    for device_type, device_label in FirmwareFile.DEVICE_CHOICES:
        count = FirmwareFile.objects.filter(device_type=device_type).count()
        percentage = (count / total_firmwares * 100) if total_firmwares > 0 else 0
        firmware_by_device.append({
            'name': device_label,
            'count': count,
            'percentage': percentage
        })
    
    # Flashing sessions gần đây
    recent_sessions = FlashingSession.objects.select_related('firmware').order_by('-flashed_at')[:10]
    
    return render(request, 'firmware/stats.html', {
        'total_firmwares': total_firmwares,
        'active_firmwares': active_firmwares,
        'total_flashes': total_flashes,
        'successful_flashes': successful_flashes,
        'success_rate': (successful_flashes / total_flashes * 100) if total_flashes > 0 else 0,
        'firmware_by_device': firmware_by_device,
        'recent_sessions': recent_sessions
    })
