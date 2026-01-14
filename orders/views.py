from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth import get_user_model
from django.contrib import messages  # Đã import sẵn
from .models import Order
from orders.forms import OrderForm, ReviewForm  
from .models import Product

User = get_user_model()

# --- DASHBOARD KỸ THUẬT VIÊN ---
@permission_required('orders.manage_order', raise_exception=True)
def tech_dashboard(request):
    jobs = Order.objects.filter(
        assigned_to=request.user, 
        status__in=['Surveying', 'Designing', 'Deploying']
    ).order_by('-created_at')
    
    return render(request, 'products/staff/tech_dashboard.html', {'jobs': jobs})

@permission_required('orders.manage_order', raise_exception=True)
def update_job_status(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES): 
            order.status = new_status
            order.save()
            # Thêm thông báo thành công
            messages.success(request, f"Đã cập nhật trạng thái đơn hàng #{order.id} sang {order.get_status_display()}.")
        else:
            messages.error(request, "Trạng thái không hợp lệ.")
    return redirect('tech_dashboard')


# --- QUY TRÌNH ĐẶT HÀNG (KHÁCH HÀNG) ---
@login_required
def create_order_direct(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.product = product
            order.total = product.price 
            order.status = 'Pending'
            order.save()
            # Thông báo cho khách hàng
            messages.success(request, "Đặt hàng thành công! Chúng tôi sẽ sớm liên hệ với bạn.")
            return redirect('my_orders') 
        else:
            messages.error(request, "Có lỗi xảy ra trong quá trình đặt hàng. Vui lòng kiểm tra lại thông tin.")
    else:
        form = OrderForm()

    return render(request, 'products/checkout.html', {
        'product': product,
        'form': form
    })

@login_required
def my_orders_view(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'orders': orders,
        'title': 'Đơn hàng của tôi'
    }
    return render(request, 'orders/my_orders.html', context)


# --- QUẢN LÝ ĐƠN HÀNG (ADMIN/STAFF) ---
@permission_required("orders.manage_order", raise_exception=True)
def order_manage_view(request):
    # CẬP NHẬT DÒNG NÀY: Dùng select_related để lấy luôn User và Profile của User đó
    orders = Order.objects.select_related('user', 'user__profile', 'product', 'assigned_to').all().order_by('-created_at')
    
    # Tương tự cho nhân viên kỹ thuật để hiện SĐT trong ô chọn (Select box)
    staff_members = User.objects.filter(is_staff=True).select_related('profile')
    
    context = {
        'orders': orders,
        'staff_members': staff_members,
        'total_orders': orders.count(),
    }
    return render(request, 'orders/manage_order.html', context)

@permission_required("orders.manage_order", raise_exception=True)
def assign_technician(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        staff_id = request.POST.get('staff_id')
        note = request.POST.get('note')
        
        if staff_id:
            try:
                tech_user = User.objects.get(id=staff_id)
                order.assigned_to = tech_user
                
                # Ghi chú cho admin
                if order.status == 'Pending':
                    messages.info(request, f"Đã gán {tech_user.username}. Đừng quên chuyển trạng thái 'Chờ duyệt' sang 'Khảo sát' để khách hàng thấy thông tin kỹ thuật viên.")

                if not hasattr(tech_user, 'profile') or not tech_user.profile.phone:
                    messages.warning(request, f"Lưu ý: Nhân viên {tech_user.username} chưa cập nhật SĐT.")
            except User.DoesNotExist:
                messages.error(request, "Nhân viên không tồn tại.")
        else:
            order.assigned_to = None
            
        order.note = note
        order.save()
        messages.success(request, f"Đã cập nhật điều phối cho đơn hàng #{order.id}")
    return redirect('order_manage_view')
@permission_required("orders.manage_order", raise_exception=True)
def update_order_status(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        
        # Chặn nếu đơn đã đóng
        if order.is_locked:
            messages.error(request, "Đơn hàng này đã hoàn thành hoặc đã hủy, không thể thay đổi trạng thái.")
            return redirect('order_manage_view')

        new_status = request.POST.get('status')
        if new_status:
            order.status = new_status
            order.save()
            messages.success(request, f"Đã cập nhật trạng thái đơn #{order.id}")
            
    return redirect('order_manage_view')

@permission_required("orders.manage_order", raise_exception=True)
def delete_order(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        order.delete()
        messages.warning(request, f"Đã xóa vĩnh viễn đơn hàng #{order_id}")
    return redirect('order_manage_view')
@login_required
def submit_review(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.status != 'Completed':
        messages.error(request, "Đơn hàng chưa hoàn thành.")
        return redirect('my_orders')

    # Tìm review cũ nếu có
    review_instance = getattr(order, 'review', None)

    if request.method == 'POST':
        form = ReviewForm(request.POST, request.FILES, instance=review_instance)
        if form.is_valid():
            review = form.save(commit=False)
            review.order = order
            review.user = request.user
            review.save()
            
            if review_instance:
                messages.success(request, "Đã cập nhật đánh giá của bạn!")
            else:
                messages.success(request, "Cảm ơn bạn đã đánh giá!")
        else:
            messages.error(request, "Dữ liệu không hợp lệ.")
            
    return redirect('my_orders')

@login_required
def delete_review(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if hasattr(order, 'review'):
        order.review.delete()
        messages.success(request, "Đã xóa đánh giá của bạn.")
    return redirect('my_orders')