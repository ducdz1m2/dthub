from django.contrib.auth.decorators import permission_required, login_required
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages  # Import framework thông báo
from django.urls import reverse
from products.forms import ProductForm, ProductImageFormSet
from .models import Product
from orders.models import Order

# --- VIEW CÔNG KHAI ---

def product_list(request):
    products = Product.objects.filter(is_active=True)
    return render(request, "products/product_list.html", {"products": products})

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    return render(request, "products/product_detail.html", {"product": product})

# --- ĐẶT HÀNG ---

@login_required
def create_order_direct(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        
        Order.objects.create(
            user=request.user,
            product=product,
            total=product.price if product.price else 0,
            status='Pending'
        )
        # Thông báo đặt hàng thành công
        messages.success(request, f"Đặt hàng {product.name} thành công! Chúng tôi sẽ sớm liên hệ.")
        return redirect('my_orders') 
    
    return redirect('product_list')

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
            print("Form errors:", form.errors)
            print("Formset errors:", formset.errors)
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
            print("--- LỖI FORM CHÍNH: ---", form.errors)
            print("--- LỖI FORMSET: ---", formset.errors)
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