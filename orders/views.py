from django.http import HttpResponse
from django.contrib.auth.decorators import permission_required

@permission_required("orders.manage_order", raise_exception=True)
def order_manage_view(request):
    return HttpResponse("Staff product: quản lý đơn hàng")
