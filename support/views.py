from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.urls import reverse
from .models import SupportRequest, SupportResponse, SupportAttachment
from .forms import SupportRequestForm, SupportResponseForm, SupportAttachmentFormSet

User = get_user_model()

@login_required
def create_support_request(request):
    if request.method == 'POST':
        form = SupportRequestForm(request.POST, request.FILES)
        formset = SupportAttachmentFormSet(request.POST, request.FILES)
        
        if form.is_valid() and formset.is_valid():
            support_request = form.save(commit=False)
            support_request.user = request.user
            support_request.save()
            
            # Save attachments
            attachments = formset.save(commit=False)
            for attachment in attachments:
                attachment.support_request = support_request
                attachment.filename = attachment.file.name
                attachment.save()
            
            messages.success(request, "Yêu cầu hỗ trợ đã được gửi thành công!")
            return redirect('my_support_requests')
        else:
            messages.error(request, "Có lỗi xảy ra. Vui lòng kiểm tra lại thông tin.")
    else:
        form = SupportRequestForm()
        formset = SupportAttachmentFormSet()
    
    return render(request, 'support/create_request.html', {
        'form': form,
        'formset': formset
    })

@login_required
def my_support_requests(request):
    page = request.GET.get('page', 1)
    per_page = 5
    
    requests = SupportRequest.objects.filter(user=request.user).order_by('-created_at')
    paginator = Paginator(requests, per_page)
    
    try:
        requests_page = paginator.page(page)
    except:
        requests_page = paginator.page(1)
    
    # Handle AJAX request for load more
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        requests_data = []
        for req in requests_page:
            requests_data.append({
                'id': req.id,
                'title': req.title,
                'category': req.get_category_display(),
                'priority': req.get_priority_display(),
                'status': req.get_status_display(),
                'created_at': req.created_at.strftime('%d/%m/%Y %H:%M'),
                'assigned_to': {
                    'username': req.assigned_to.username if req.assigned_to else None,
                    'avatar': req.assigned_to.profile.avatar.url if req.assigned_to and hasattr(req.assigned_to, 'profile') and req.assigned_to.profile.avatar else None
                } if req.assigned_to else None,
                'response_count': req.responses.count()
            })
        
        return JsonResponse({
            'requests': requests_data,
            'has_next': requests_page.has_next(),
            'current_page': requests_page.number,
            'total_pages': paginator.num_pages
        })
    
    context = {
        'requests': requests_page,
        'title': 'Yêu cầu hỗ trợ của tôi',
        'has_next': requests_page.has_next(),
        'current_page': requests_page.number,
        'total_pages': paginator.num_pages
    }
    return render(request, 'support/my_requests.html', context)

@login_required
def support_request_detail(request, request_id):
    support_request = get_object_or_404(SupportRequest, id=request_id)
    
    # Check permissions
    if support_request.user != request.user and not request.user.is_staff:
        messages.error(request, "Bạn không có quyền xem yêu cầu này.")
        return redirect('my_support_requests')
    
    if request.method == 'POST':
        form = SupportResponseForm(request.POST)
        if form.is_valid():
            response = form.save(commit=False)
            response.support_request = support_request
            response.author = request.user
            response.save()
            
            # Update status if this is first staff response
            if support_request.status == 'Pending' and request.user.is_staff:
                support_request.status = 'In_Progress'
                support_request.save()
            
            messages.success(request, "Phản hồi đã được gửi!")
            return redirect('support_request_detail', request_id=request_id)
    else:
        form = SupportResponseForm()
    
    return render(request, 'support/request_detail.html', {
        'support_request': support_request,
        'form': form,
        'responses': support_request.responses.order_by('created_at'),
        'attachments': support_request.attachments.all()
    })

@permission_required('support.manage_support_request', raise_exception=True)
def support_manage_view(request):
    page = request.GET.get('page', 1)
    per_page = 5
    
    requests = SupportRequest.objects.select_related('user', 'user__profile', 'assigned_to').all().order_by('-created_at')
    paginator = Paginator(requests, per_page)
    
    try:
        requests_page = paginator.page(page)
    except:
        requests_page = paginator.page(1)
    
    # Handle AJAX request for load more
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        requests_data = []
        for req in requests_page:
            requests_data.append({
                'id': req.id,
                'title': req.title,
                'category': req.get_category_display(),
                'priority': req.get_priority_display(),
                'status': req.get_status_display(),
                'created_at': req.created_at.strftime('%d/%m/%Y %H:%M'),
                'user': {
                    'username': req.user.username,
                    'email': req.user.email,
                    'phone': req.user.profile.phone if hasattr(req.user, 'profile') and req.user.profile.phone else None
                },
                'assigned_to': {
                    'username': req.assigned_to.username if req.assigned_to else None,
                    'id': req.assigned_to.id if req.assigned_to else None
                } if req.assigned_to else None,
                'response_count': req.responses.count()
            })
        
        return JsonResponse({
            'requests': requests_data,
            'has_next': requests_page.has_next(),
            'current_page': requests_page.number,
            'total_pages': paginator.num_pages
        })
    
    staff_members = User.objects.filter(is_staff=True).select_related('profile')
    
    context = {
        'requests': requests_page,
        'staff_members': staff_members,
        'total_requests': requests.count(),
        'has_next': requests_page.has_next(),
        'current_page': requests_page.number,
        'total_pages': paginator.num_pages
    }
    return render(request, 'support/manage_requests.html', context)

@permission_required('support.manage_support_request', raise_exception=True)
def assign_support_staff(request, request_id):
    if request.method == 'POST':
        support_request = get_object_or_404(SupportRequest, id=request_id)
        staff_id = request.POST.get('staff_id')
        
        if staff_id:
            try:
                staff_user = User.objects.get(id=staff_id)
                support_request.assigned_to = staff_user
                support_request.save()
                messages.success(request, f"Đã gán {staff_user.username} phụ trách yêu cầu #{support_request.id}")
            except User.DoesNotExist:
                messages.error(request, "Nhân viên không tồn tại.")
        else:
            support_request.assigned_to = None
            support_request.save()
            messages.success(request, f"Đã bỏ gán nhân viên cho yêu cầu #{support_request.id}")
    
    return redirect('support_manage_view')

@permission_required('support.manage_support_request', raise_exception=True)
def update_support_status(request, request_id):
    if request.method == 'POST':
        support_request = get_object_or_404(SupportRequest, id=request_id)
        new_status = request.POST.get('status')
        
        if new_status in dict(SupportRequest.STATUS_CHOICES):
            old_status = support_request.status
            support_request.status = new_status
            
            # Set resolved_at when status is changed to Resolved
            if new_status == 'Resolved' and old_status != 'Resolved':
                from django.utils import timezone
                support_request.resolved_at = timezone.now()
            elif new_status != 'Resolved':
                support_request.resolved_at = None
                
            support_request.save()
            messages.success(request, f"Đã cập nhật trạng thái yêu cầu #{support_request.id}")
        else:
            messages.error(request, "Trạng thái không hợp lệ.")
    
    return redirect('support_manage_view')
