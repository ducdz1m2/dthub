from django.http import HttpResponse
from django.contrib.auth.decorators import permission_required

@permission_required("products.manage_product", raise_exception=True)
def product_manage_view(request):
    return HttpResponse("Staff product: quản lý sản phẩm")
