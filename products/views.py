from django.contrib.auth.decorators import permission_required, login_required
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages  # Import framework thông báo
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db.models import Q
from products.forms import ProductForm, ProductImageFormSet
from .models import Product

User = get_user_model()

# --- VIEW CÔNG KHAI ---

def product_list(request):
    products = Product.objects.filter(is_active=True)
    return render(request, "products/product_list.html", {"products": products})

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    return render(request, "products/product_detail.html", {"product": product})

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
            return redirect('product_list')
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
            return redirect('product_list')
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
        return redirect(reverse("product_list"))
    
    # Nếu truy cập bằng GET, chuyển hướng về danh sách
    return redirect(reverse("product_list"))

@login_required
def product_consultation(request, pk):
    """Xử lý tư vấn sản phẩm - chuyển đến chat với staff và gửi thông tin sản phẩm"""
    product = get_object_or_404(Product, pk=pk, is_active=True)
    
    # Tìm staff có thể tư vấn (ProductOrderManager hoặc superuser)
    admin_groups = ["ProductOrderManager", "ContentFeedbackManager", "AIArchitect"]
    staff_users = User.objects.filter(
        Q(groups__name__in=admin_groups) | Q(is_superuser=True)
    ).distinct().exclude(id=request.user.id)
    
    if not staff_users.exists():
        messages.error(request, "Hiện không có nhân viên nào trực để tư vấn. Vui lòng thử lại sau.")
        return redirect('product_detail', product.slug)
    
    # Lấy staff đầu tiên có sẵn (có thể nâng cấp để chọn staff online)
    staff_user = staff_users.first()
    
    # Tạo thông điệp tư vấn với thông tin sản phẩm
    price_text = f"{product.price:,}₫" if product.price else "Liên hệ báo giá"
    description_text = ' '.join(product.description.split()[:30]) + ('...' if len(product.description.split()) > 30 else '') if product.description else 'Không có mô tả'
    product_info = f"""🛍️ TƯ VẤN SẢN PHẨM<br><br>📦 Tên sản phẩm: {product.name}<br>🏷️ Loại sản phẩm: {product.get_product_type_display()}<br>💰 Giá: {price_text}<br>📝 Mô tả: {description_text}<br>🔗 Link: {request.build_absolute_uri(reverse('product_detail', args=[product.slug]))}<br><br>Tôi quan tâm đến sản phẩm này, vui lòng tư vấn thêm ạ!"""
    
    # Lưu thông tin sản phẩm vào session để hiển thị trong chat
    request.session['consultation_product_info'] = product_info
    request.session.save()  # Force save session
    
    # Chuyển đến phòng chat với staff
    return redirect('chat_room', staff_user.id)