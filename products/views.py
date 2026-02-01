from django.contrib.auth.decorators import permission_required, login_required
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages  # Import framework thông báo
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from products.forms import ProductForm, ProductImageFormSet
from .models import Product

User = get_user_model()

# --- VIEW CÔNG KHAI ---

def product_list(request):
    page = request.GET.get('page', 1)
    per_page = 5  # Show 5 products per page
    product_type = request.GET.get('type', 'all')
    
    # Check if user can manage products
    can_manage = request.user.has_perm('products.manage_product')
    
    # Show all products for managers, only active products for regular users
    if can_manage:
        products = Product.objects.all()
    else:
        products = Product.objects.filter(is_active=True)
    
    # Filter by product type if specified
    if product_type != 'all':
        products = products.filter(product_type=product_type)
    
    paginator = Paginator(products, per_page)
    
    try:
        products_page = paginator.page(page)
    except:
        products_page = paginator.page(1)
    
    # Handle AJAX request for load more
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        products_data = []
        for product in products_page:
            product_data = {
                'id': product.id,
                'name': product.name,
                'slug': product.slug,
                'description': product.description[:100] + '...' if product.description and len(product.description) > 100 else product.description,
                'price': product.price,
                'product_type': product.product_type,
                'product_type_display': product.get_product_type_display(),
                'is_active': product.is_active,
                'image_url': None,
                'detail_url': reverse('products:product_detail', args=[product.slug]),
                'order_url': reverse('orders:create_order_direct', args=[product.id]),
                'consultation_url': reverse('products:product_consultation', args=[product.id])
            }
            
            # Add image if exists
            if product.images.exists():
                product_data['image_url'] = product.images.first().image.url
            else:
                product_data['image_url'] = '/static/images/default-product.webp'
            
            products_data.append(product_data)
        
        return JsonResponse({
            'products': products_data,
            'has_next': products_page.has_next(),
            'current_page': products_page.number,
            'total_pages': paginator.num_pages,
            'product_type': product_type,
            'can_manage': can_manage
        })
    
    context = {
        "products": products_page,
        "has_next": products_page.has_next(),
        "current_page": products_page.number,
        "total_pages": paginator.num_pages,
        "current_type": product_type,
        "can_manage": can_manage
    }
    return render(request, "products/product_list.html", context)

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    
    # Debug: Try to render the template step by step
    try:
        context = {"product": product}
        return render(request, "products/product_detail.html", context)
    except Exception as e:
        # If template rendering fails, return error details
        return HttpResponse(f"Template Error: {str(e)}")

# --- QUẢN LÝ SẢN PHẨM (ADMIN) ---

@permission_required('products.manage_product', raise_exception=True)
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES) 
        formset = ProductImageFormSet(request.POST, request.FILES)

        if form.is_valid() and formset.is_valid():
            product = form.save()
            formset.instance = product
            formset.save()
            # Thông báo tạo mới thành công
            messages.success(request, f"Đã thêm sản phẩm '{product.name}' thành công.")
            return redirect('products:product_list')
        else:
            messages.error(request, "Có lỗi xảy ra. Vui lòng kiểm tra lại thông tin nhập vào.")
    else:
        form = ProductForm()
        formset = ProductImageFormSet()

    return render(request, "products/admin/product_form.html", {
        "form": form,
        "formset": formset,
    })

@permission_required('products.manage_product', raise_exception=True)
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        formset = ProductImageFormSet(request.POST, request.FILES, instance=product)

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            # Thông báo cập nhật thành công
            messages.success(request, f"Cập nhật sản phẩm '{product.name}' thành công.")
            return redirect('products:product_list')
        else:
            messages.error(request, "Không thể cập nhật sản phẩm. Vui lòng kiểm tra lại dữ liệu.")
    else:
        form = ProductForm(instance=product)
        formset = ProductImageFormSet(instance=product)

    return render(request, "products/admin/product_form.html", {
        "form": form,
        "formset": formset,
        "product": product
    })

@permission_required('products.manage_product', raise_exception=True)
def product_delete(request, pk):
    # Dùng POST để xóa an toàn hơn (tránh xóa nhầm qua link GET)
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=pk)
        name = product.name
        product.delete()
        messages.warning(request, f"Đã xóa sản phẩm '{name}'.")
        return redirect(reverse("products:product_list"))
    
    # Nếu truy cập bằng GET, chuyển hướng về danh sách
    return redirect(reverse("products:product_list"))

@login_required
def product_consultation(request, pk):
    """Xử lý tư vấn sản phẩm - chuyển đến chat với staff và gửi thông tin sản phẩm"""
    product = get_object_or_404(Product, pk=pk, is_active=True)
    
    # Tìm staff có thể tư vấn (ProductOrderManager hoặc superuser)
    admin_groups = ["ProductOrderManager", "ContentFeedbackManager", "AIArchitect"]
    staff_users = User.objects.filter(
        Q(groups__name__in=admin_groups) | Q(is_superuser=True)
    ).distinct().exclude(id=request.user.id)
    
    # Nếu không tìm được staff khả dụng, gán cho admin (superuser đầu tiên)
    if not staff_users.exists():
        admin_user = User.objects.filter(is_superuser=True).exclude(id=request.user.id).first()
        if admin_user:
            staff_user = admin_user
            messages.info(request, f"Đang chuyển đến admin để tư vấn sản phẩm.")
        else:
            messages.error(request, "Hiện không có nhân viên nào trực để tư vấn. Vui lòng thử lại sau.")
            return redirect('products:product_detail', product.slug)
    else:
        # Lấy staff đầu tiên có sẵn (có thể nâng cấp để chọn staff online)
        staff_user = staff_users.first()
    
    # Tạo thông điệp tư vấn với thông tin sản phẩm
    price_text = f"{product.price:,}₫" if product.price else "Liên hệ báo giá"
    description_text = ' '.join(product.description.split()[:30]) + ('...' if len(product.description.split()) > 30 else '') if product.description else 'Không có mô tả'
    product_info = f"""🛍️ TƯ VẤN SẢN PHẨM<br><br>📦 Tên sản phẩm: {product.name}<br>🏷️ Loại sản phẩm: {product.get_product_type_display()}<br>💰 Giá: {price_text}<br>📝 Mô tả: {description_text}<br>🔗 Link: {request.build_absolute_uri(reverse('products:product_detail', args=[product.slug]))}<br><br>Tôi quan tâm đến sản phẩm này, vui lòng tư vấn thêm ạ!"""
    
    # Lưu thông tin sản phẩm vào session để hiển thị trong chat
    request.session['consultation_product_info'] = product_info
    
    # Chuyển đến phòng chat với staff
    return redirect(reverse('chat_room', args=[staff_user.id]))