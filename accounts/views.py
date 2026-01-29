from django.contrib.auth.models import Group
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages
from .forms import ProfileUpdateForm
import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from .forms import StaffCreationForm
from django.core.paginator import Paginator

User = get_user_model()


@login_required
def update_location(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            lat = data.get('lat')
            lng = data.get('lng')
            
            # Validate latitude (-90 to 90)
            if lat is not None and (lat < -90 or lat > 90):
                return JsonResponse({'status': 'error', 'message': 'Latitude phải nằm trong khoảng -90 đến 90'}, status=400)
            
            # Validate longitude (-180 to 180)
            if lng is not None and (lng < -180 or lng > 180):
                return JsonResponse({'status': 'error', 'message': 'Longitude phải nằm trong khoảng -180 đến 180'}, status=400)
            
            profile = request.user.profile
            profile.current_lat = lat
            profile.current_lng = lng
            profile.save()
            return JsonResponse({'status': 'success'})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Dữ liệu JSON không hợp lệ'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'invalid method'}, status=405)

@login_required
def profile_view(request):
    # Lấy profile của user hiện tại, nếu chưa có (do lỗi cũ) thì Signal đã tạo ở model rồi
    profile = request.user.profile
    
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Hồ sơ của bạn đã được cập nhật!")
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=profile)
    
    return render(request, 'accounts/profile.html', {'form': form})

@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, "Bạn đã đăng xuất thành công.")
    return redirect("/")

def auth_view(request):
    if request.method == "POST":
        action = request.POST.get("action")
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        email = request.POST.get("email", "").strip()  # Lấy thêm email từ POST data

        # Kiểm tra chung cho cả Login và Register
        if not username or not password:
            messages.error(request, "Vui lòng nhập đầy đủ username và password.")
            return redirect("auth")

        if action == "login":
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                messages.success(request, "Đăng nhập thành công.")
                return redirect("/")
            else:
                messages.error(request, "Sai username hoặc mật khẩu.")
                return redirect("auth")

        elif action == "register":
            # 1. Kiểm tra username tồn tại
            if User.objects.filter(username=username).exists():
                messages.error(request, "Username này đã được sử dụng.")
                return redirect("auth")
            
            # 2. Kiểm tra Email (Bắt buộc khi đăng ký để phục vụ Reset Password)
            if not email:
                messages.error(request, "Vui lòng cung cấp Email để có thể khôi phục mật khẩu sau này.")
                return redirect("auth")
            
            if User.objects.filter(email=email).exists():
                messages.error(request, "Email này đã được đăng ký cho một tài khoản khác.")
                return redirect("auth")

            # 3. Tạo User kèm theo Email
            try:
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    email=email  # Quan trọng: Lưu email vào database
                )
                login(request, user)
                messages.success(request, "Đăng ký thành công và đã đăng nhập.")
                return redirect("/")
            except Exception as e:
                messages.error(request, f"Có lỗi xảy ra trong quá trình đăng ký: {e}")
                return redirect("auth")

    return render(request, "accounts/auth.html")


@permission_required('accounts.view_user', raise_exception=True)
def manage_staff_list(request):
    page = request.GET.get('page', 1)
    per_page = 10  # Show 10 staff members per page
    
    # Lấy tất cả user là nhân viên (is_staff=True)
    staffs = User.objects.filter(is_staff=True).prefetch_related('groups', 'profile')
    
    paginator = Paginator(staffs, per_page)
    
    try:
        staffs_page = paginator.page(page)
    except:
        staffs_page = paginator.page(1)
    
    # Handle AJAX request for load more
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        staffs_data = []
        for staff in staffs_page:
            staff_data = {
                'id': staff.id,
                'username': staff.username,
                'email': staff.email,
                'phone': staff.profile.phone if hasattr(staff, 'profile') and staff.profile.phone else '-',
                'avatar_url': staff.profile.get_avatar_url() if hasattr(staff, 'profile') else '/static/images/avatar-default.png',
                'is_active': staff.is_active,
                'is_superuser': staff.is_superuser,
                'is_online': False,  # Will be updated by WebSocket
                'groups': [{'name': group.name} for group in staff.groups.all()],
                'edit_url': f'/accounts/staff/edit/{staff.id}/',
                'toggle_url': f'/accounts/staff/toggle/{staff.id}/',
                'delete_url': f'/accounts/staff/delete/{staff.id}/'
            }
            staffs_data.append(staff_data)
        
        return JsonResponse({
            'staffs': staffs_data,
            'has_next': staffs_page.has_next(),
            'current_page': staffs_page.number,
            'total_pages': paginator.num_pages
        })
    
    context = {
        'staffs': staffs_page,
        'has_next': staffs_page.has_next(),
        'current_page': staffs_page.number,
        'total_pages': paginator.num_pages
    }
    return render(request, 'accounts/staff_list.html', context)

@permission_required('accounts.add_user', raise_exception=True)
def create_staff_view(request):
    if request.method == 'POST':
        form = StaffCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Đã tạo thành công tài khoản cho {user.username} (Email: {user.email})")
            return redirect('manage_staff_list')
        else:
            messages.error(request, "Vui lòng kiểm tra lại thông tin nhập vào.")
    else:
        form = StaffCreationForm()
    
    return render(request, 'accounts/create_staff.html', {'form': form})


@permission_required('accounts.change_user', raise_exception=True)
def edit_staff(request, staff_id):
    staff = get_object_or_404(User, id=staff_id, is_staff=True)
    
    # Ngăn sửa thông tin superuser (admin) - chỉ có superuser mới được sửa superuser khác
    if staff.is_superuser and not request.user.is_superuser:
        messages.error(request, "Bạn không thể chỉnh sửa thông tin Administrator!")
        return redirect('manage_staff_list')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        role_id = request.POST.get('role')
        new_password = request.POST.get('new_password') # Lấy mật khẩu mới
        
        staff.username = username
        staff.email = email
        
        # Xử lý đổi mật khẩu nếu có nhập
        if new_password and len(new_password.strip()) > 0:
            staff.set_password(new_password)
            # Nếu admin tự đổi pass cho chính mình, cần update_session_auth_hash để không bị văng login
            # Nhưng ở đây là admin đổi cho nhân viên nên không cần lo lắng.
        
        if role_id:
            role = Group.objects.get(id=role_id)
            staff.groups.clear()
            staff.groups.add(role)
            
        staff.save()
        messages.success(request, f"Cập nhật nhân viên {staff.username} thành công.")
        return redirect('manage_staff_list')
    
    roles = Group.objects.all()
    return render(request, 'accounts/edit_staff.html', {'staff': staff, 'roles': roles})

@permission_required('accounts.delete_user', raise_exception=True)
@require_POST
def delete_staff(request, staff_id):
    staff = get_object_or_404(User, id=staff_id, is_staff=True)
    
    # Ngăn xóa superuser (admin) - chỉ có superuser mới được xóa superuser khác
    if staff.is_superuser and not request.user.is_superuser:
        messages.error(request, "Bạn không thể xóa tài khoản Administrator!")
        return redirect('manage_staff_list')
    
    # Ngăn admin tự xóa chính mình
    if staff == request.user:
        messages.error(request, "Bạn không thể tự xóa tài khoản của chính mình!")
        return redirect('manage_staff_list')
        
    username = staff.username
    staff.delete()
    messages.success(request, f"Đã xóa vĩnh viễn nhân viên {username}.")
    return redirect('manage_staff_list')

@permission_required('accounts.change_user', raise_exception=True)
def toggle_staff_status(request, staff_id):
    if request.method == 'POST':
        staff = get_object_or_404(User, id=staff_id)
        
        # Ngăn khóa tài khoản superuser (admin)
        if staff.is_superuser:
            messages.error(request, "Bạn không thể khóa tài khoản Administrator!")
            return redirect('manage_staff_list')
        
        staff.is_active = not staff.is_active # Đảo ngược trạng thái
        staff.save()
        status = "mở khóa" if staff.is_active else "khóa"
        messages.warning(request, f"Đã {status} tài khoản {staff.username}.")
    return redirect('manage_staff_list')