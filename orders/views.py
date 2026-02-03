from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth import get_user_model
from django.contrib import messages  # Đã import sẵn
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.urls import reverse
from .models import Order, Payment
from .forms import OrderForm, ReviewForm  
from .vnpay_service import VNPayService
from products.models import Product

User = get_user_model()

# --- DASHBOARD KỸ THUẬT VIÊN ---
@permission_required('orders.manage_order', raise_exception=True)
def tech_dashboard(request):
    page = request.GET.get('page', 1)
    per_page = 5  # Show 5 orders per page
    
    jobs = Order.objects.filter(
        assigned_to=request.user, 
        status__in=['Surveying', 'Designing', 'Deploying']
    ).order_by('-created_at')
    paginator = Paginator(jobs, per_page)
    
    try:
        jobs_page = paginator.page(page)
    except:
        jobs_page = paginator.page(1)
    
    # Handle AJAX request for load more
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        jobs_data = []
        for job in jobs_page:
            jobs_data.append({
                'id': job.id,
                'product_name': job.product.name,
                'total': job.total,
                'status': job.status,
                'status_display': job.get_status_display(),
                'created_at': job.created_at.strftime('%d/%m/%Y'),
                'address': job.address or 'Đang xác nhận địa chỉ...',
                'note': job.note or 'Thông tin triển khai sẽ được cập nhật sớm nhất.',
                'assigned_to': None,
                'review': None,
                'is_locked': job.is_locked
            })
            
            # Add technician info if assigned
            if job.assigned_to and job.status != 'Pending':
                jobs_data[-1]['assigned_to'] = {
                    'username': job.assigned_to.get_full_name() or job.assigned_to.username,
                    'phone': job.assigned_to.profile.phone if hasattr(job.assigned_to, 'profile') and job.assigned_to.profile.phone else None,
                    'avatar': job.assigned_to.profile.avatar.url if hasattr(job.assigned_to, 'profile') and job.assigned_to.profile.avatar and 'default.png' not in job.assigned_to.profile.avatar.url else None
                }
            
            # Add review info if exists
            if hasattr(job, 'review') and job.review:
                jobs_data[-1]['review'] = {
                    'rating': job.review.rating,
                    'comment': job.review.comment,
                    'image': job.review.image.url if job.review.image else None
                }
        
        return JsonResponse({
            'jobs': jobs_data,
            'has_next': jobs_page.has_next(),
            'current_page': jobs_page.number,
            'total_pages': paginator.num_pages
        })
    
    context = {
        'jobs': jobs_page,
        'has_next': jobs_page.has_next(),
        'current_page': jobs_page.number,
        'total_pages': paginator.num_pages
    }
    return render(request, 'products/staff/tech_dashboard.html', context)

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
    return redirect('orders:tech_dashboard')


# --- QUY TRÌNH ĐẶT HÀNG (KHÁCH HÀNG) ---
@login_required
def create_order_direct(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        form = OrderForm(request.POST)
        payment_method = request.POST.get('payment_method', 'vnpay')
        
        # Check for duplicate order in last 5 minutes
        from django.utils import timezone
        from datetime import timedelta
        recent_time = timezone.now() - timedelta(minutes=5)
        duplicate_order = Order.objects.filter(
            user=request.user,
            product=product,
            created_at__gte=recent_time
        ).first()
        
        if duplicate_order:
            messages.warning(request, f"Bạn đã đặt đơn hàng cho sản phẩm này trong vòng 5 phút qua. Vui lòng kiểm tra đơn hàng #{duplicate_order.id} trong lịch sử đơn hàng.")
            return redirect('orders:my_orders')
        
        if form.is_valid():
            from django.db import transaction
            try:
                with transaction.atomic():
                    order = form.save(commit=False)
                    order.user = request.user
                    order.product = product
                    order.total = product.price 
                    order.status = 'Pending'
                    order.save()
                    
                    # Tạo payment
                    payment = Payment.objects.create(
                        order=order,
                        method=payment_method,
                        amount=order.total,
                        status='pending'
                    )
                    
                    if payment_method == 'vnpay':
                        # Chuyển hướng đến VNPay
                        vnpay_service = VNPayService()
                        payment_url = vnpay_service.create_payment_url(payment, request)
                        return redirect(payment_url)
                    
                    elif payment_method == 'cod':
                        # Đánh dấu là COD và hoàn tất
                        payment.status = 'pending'  # Chờ thanh toán khi giao hàng
                        payment.save()
                        messages.success(request, "Đặt hàng thành công! Chúng tôi sẽ giao hàng và thu tiền khi nhận hàng.")
                        return redirect('orders:payment_success', payment_id=payment.id)
                        
            except Exception as e:
                messages.error(request, f"Có lỗi xảy ra khi tạo đơn hàng: {str(e)}")
                return redirect('products:product_detail', slug=product.slug)
            
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
    page = request.GET.get('page', 1)
    per_page = 5  # Show 5 orders per page
    
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    paginator = Paginator(orders, per_page)
    
    try:
        orders_page = paginator.page(page)
    except:
        orders_page = paginator.page(1)
    
    # Handle AJAX request for load more
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        orders_data = []
        for order in orders_page:
            orders_data.append({
                'id': order.id,
                'product_name': order.product.name,
                'total': order.total,
                'status': order.status,
                'status_display': order.get_status_display(),
                'created_at': order.created_at.strftime('%d/%m/%Y'),
                'address': order.address or 'Đang xác nhận địa chỉ...',
                'note': order.note or 'Thông tin triển khai sẽ được cập nhật sớm nhất.',
                'assigned_to': None,
                'review': None,
                'is_locked': order.is_locked
            })
            
            # Add technician info if assigned
            if order.assigned_to and order.status != 'Pending':
                orders_data[-1]['assigned_to'] = {
                    'username': order.assigned_to.get_full_name() or order.assigned_to.username,
                    'phone': order.assigned_to.profile.phone if hasattr(order.assigned_to, 'profile') and order.assigned_to.profile.phone else None,
                    'avatar': order.assigned_to.profile.avatar.url if hasattr(order.assigned_to, 'profile') and order.assigned_to.profile.avatar and 'default.png' not in order.assigned_to.profile.avatar.url else None
                }
            
            # Add review info if exists
            if hasattr(order, 'review') and order.review:
                orders_data[-1]['review'] = {
                    'rating': order.review.rating,
                    'comment': order.review.comment,
                    'image': order.review.image.url if order.review.image else None
                }
            
            # Add payment information
            orders_data[-1]['payment_status'] = order.payment_status
            orders_data[-1]['is_paid'] = order.is_paid
            if hasattr(order, 'payment'):
                orders_data[-1]['payment'] = {
                    'status': order.payment.status,
                    'method': order.payment.get_method_display(),
                    'amount': str(order.payment.amount),
                    'completed_at': order.payment.completed_at.strftime('%d/%m/%Y %H:%M') if order.payment.completed_at else None
                }
        
        return JsonResponse({
            'orders': orders_data,
            'has_next': orders_page.has_next(),
            'current_page': orders_page.number,
            'total_pages': paginator.num_pages
        })
    
    context = {
        'orders': orders_page,
        'title': 'Đơn hàng của tôi',
        'has_next': orders_page.has_next(),
        'current_page': orders_page.number,
        'total_pages': paginator.num_pages
    }
    return render(request, 'orders/my_orders.html', context)

@login_required
def cancel_order(request, order_id):
    """Hủy đơn hàng từ phía khách hàng với giới hạn trạng thái"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Chỉ cho phép hủy ở các trạng thái nhất định
    CANCELLABLE_STATUSES = ['Pending', 'Surveying', 'Designing']
    
    if order.status not in CANCELLABLE_STATUSES:
        messages.error(request, f"Không thể hủy đơn hàng ở trạng thái '{order.get_status_display()}'. Đơn hàng chỉ có thể được hủy khi đang ở trạng thái: Chờ duyệt, Khảo sát, hoặc Thiết kế.")
        return redirect('orders:my_orders')
    
    # Nếu đã thanh toán thì không cho hủy
    if order.is_paid:
        messages.error(request, "Không thể hủy đơn hàng đã thanh toán. Vui lòng liên hệ hỗ trợ để được xử lý.")
        return redirect('orders:my_orders')
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        order.status = 'Cancelled'
        order.note = f"Khách hàng hủy đơn. Lý do: {reason}" + (f". Ghi chú cũ: {order.note}" if order.note else "")
        order.save()
        
        # Cập nhật payment status nếu có
        if hasattr(order, 'payment'):
            order.payment.status = 'cancelled'
            order.payment.save()
        
        messages.success(request, f"Đã hủy đơn hàng #{order.id} thành công.")
        return redirect('orders:my_orders')
    
    return render(request, 'orders/cancel_order.html', {
        'order': order,
        'cancellable_statuses': CANCELLABLE_STATUSES
    })


# --- QUẢN LÝ ĐƠN HÀNG (ADMIN/STAFF) ---
@permission_required("orders.manage_order", raise_exception=True)
def order_manage_view(request):
    page = request.GET.get('page', 1)
    per_page = 5  # Show 5 orders per page
    
    # CẬP NHẬT DÒNG NÀY: Dùng select_related để lấy luôn User và Profile của User đó
    orders = Order.objects.select_related('user', 'user__profile', 'product', 'assigned_to').all().order_by('-created_at')
    paginator = Paginator(orders, per_page)
    
    try:
        orders_page = paginator.page(page)
    except:
        orders_page = paginator.page(1)
    
    # Handle AJAX request for load more
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        orders_data = []
        for order in orders_page:
            orders_data.append({
                'id': order.id,
                'user': {
                    'username': order.user.username,
                    'id': order.user.id,
                    'phone': order.user.profile.phone if hasattr(order.user, 'profile') and order.user.profile.phone else None,
                    'address': order.user.profile.address if hasattr(order.user, 'profile') and order.user.profile.address else None
                },
                'product': {
                    'name': order.product.name
                },
                'total': order.total,
                'status': order.status,
                'status_display': order.get_status_display(),
                'note': order.note or '',
                'assigned_to': None,
                'review': None,
                'is_locked': order.is_locked
            })
            
            # Add technician info if assigned
            if order.assigned_to:
                orders_data[-1]['assigned_to'] = {
                    'id': order.assigned_to.id,
                    'username': order.assigned_to.username,
                    'phone': order.assigned_to.profile.phone if hasattr(order.assigned_to, 'profile') and order.assigned_to.profile.phone else None
                }
            
            # Add review info if exists
            if hasattr(order, 'review') and order.review:
                orders_data[-1]['review'] = {
                    'rating': order.review.rating,
                    'comment': order.review.comment
                }
            
            # Add payment information
            orders_data[-1]['payment_status'] = order.payment_status
            orders_data[-1]['is_paid'] = order.is_paid
            if hasattr(order, 'payment'):
                orders_data[-1]['payment'] = {
                    'status': order.payment.status,
                    'method': order.payment.get_method_display(),
                    'amount': str(order.payment.amount),
                    'completed_at': order.payment.completed_at.strftime('%d/%m/%Y %H:%M') if order.payment.completed_at else None
                }
        
        return JsonResponse({
            'orders': orders_data,
            'has_next': orders_page.has_next(),
            'current_page': orders_page.number,
            'total_pages': paginator.num_pages
        })
    
    # Tương tự cho nhân viên kỹ thuật để hiện SĐT trong ô chọn (Select box)
    staff_members = User.objects.filter(is_staff=True).select_related('profile')
    
    context = {
        'orders': orders_page,
        'staff_members': staff_members,
        'total_orders': orders.count(),
        'has_next': orders_page.has_next(),
        'current_page': orders_page.number,
        'total_pages': paginator.num_pages
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
    return redirect('orders:order_manage_view')
@permission_required("orders.manage_order", raise_exception=True)
def update_order_status(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        
        # Chặn nếu đơn đã đóng
        if order.is_locked:
            messages.error(request, "Đơn hàng này đã hoàn thành hoặc đã hủy, không thể thay đổi trạng thái.")
            return redirect('orders:order_manage_view')

        new_status = request.POST.get('status')
        if new_status:
            order.status = new_status
            order.save()
            messages.success(request, f"Đã cập nhật trạng thái đơn #{order.id}")
            
    return redirect('orders:order_manage_view')

@permission_required("orders.manage_order", raise_exception=True)
def delete_order(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        order.delete()
        messages.warning(request, f"Đã xóa vĩnh viễn đơn hàng #{order_id}")
    return redirect('orders:order_manage_view')
@login_required
def submit_review(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.status != 'Completed':
        messages.error(request, "Đơn hàng chưa hoàn thành.")
        return redirect('orders:my_orders')

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
            
    return redirect('orders:my_orders')

@login_required
def delete_review(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if hasattr(order, 'review'):
        order.review.delete()
        messages.success(request, "Đã xóa đánh giá của bạn.")
    return redirect('orders:my_orders')


# --- PAYMENT VIEWS ---
@login_required
def create_payment(request, order_id):
    """Tạo thanh toán cho đơn hàng"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Kiểm tra nếu đã có payment
    if hasattr(order, 'payment'):
        messages.warning(request, "Đơn hàng này đã có thanh toán.")
        return redirect('orders:payment_detail', payment_id=order.payment.id)
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        
        if payment_method not in ['vnpay', 'cod']:
            messages.error(request, "Phương thức thanh toán không hợp lệ.")
            return redirect('orders:create_payment', order_id=order_id)
        
        # Tạo payment
        payment = Payment.objects.create(
            order=order,
            method=payment_method,
            amount=order.total,
            status='pending'
        )
        
        if payment_method == 'vnpay':
            # Chuyển hướng đến VNPay
            vnpay_service = VNPayService()
            payment_url = vnpay_service.create_payment_url(payment, request)
            return redirect(payment_url)
        
        elif payment_method == 'cod':
            # Đánh dấu là COD và hoàn tất
            payment.status = 'pending'  # Chờ thanh toán khi giao hàng
            payment.save()
            messages.success(request, "Đặt hàng thành công! Chúng tôi sẽ giao hàng và thu tiền khi nhận hàng.")
            return redirect('orders:payment_success', payment_id=payment.id)
    
    return render(request, 'orders/create_payment.html', {
        'order': order
    })

@login_required
def payment_detail(request, payment_id):
    """Chi tiết thanh toán"""
    payment = get_object_or_404(Payment, id=payment_id, order__user=request.user)
    return render(request, 'orders/payment_detail.html', {
        'payment': payment
    })

@login_required
def payment_success(request, payment_id):
    """Trang thanh toán thành công"""
    payment = get_object_or_404(Payment, id=payment_id, order__user=request.user)
    return render(request, 'orders/payment_success.html', {
        'payment': payment
    })

@login_required
def payment_failed(request, payment_id):
    """Trang thanh toán thất bại"""
    payment = get_object_or_404(Payment, id=payment_id, order__user=request.user)
    return render(request, 'orders/payment_failed.html', {
        'payment': payment
    })

@csrf_exempt
def vnpay_return(request):
    """Xử lý callback từ VNPay"""
    if request.method == 'GET':
        vnpay_service = VNPayService()
        result = vnpay_service.verify_return(request)
        
        if result['success']:
            payment = result['payment']
            messages.success(request, "Thanh toán thành công!")
            return redirect('orders:payment_success', payment_id=payment.id)
        else:
            payment = result.get('payment')
            error_message = result['message']
            messages.error(request, f"Thanh toán thất bại: {error_message}")
            if payment:
                return redirect('orders:payment_failed', payment_id=payment.id)
            else:
                return redirect('orders:my_orders')
    
    return redirect('orders:my_orders')

@csrf_exempt
def vnpay_ipn(request):
    """IPN handler từ VNPay (server-to-server)"""
    if request.method == 'POST':
        vnpay_service = VNPayService()
        result = vnpay_service.verify_return(request)
        
        if result['success']:
            # Cập nhật trạng thái payment thành công
            return HttpResponse("RspCode=00&Message=Confirm Success")
        else:
            # Lỗi signature hoặc khác
            return HttpResponse("RspCode=97&Message=Invalid Signature")
    
    return HttpResponse("RspCode=99&Message=Invalid Request")
