from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, permission_required

@login_required
def forum_public_view(request):
    return HttpResponse("Ai đăng nhập cũng xem được forum")

@permission_required("forum.manage_post", raise_exception=True)
def forum_manage_post(request):
    return HttpResponse("Staff forum: quản lý bài đăng")

@permission_required("forum.manage_feedback", raise_exception=True)
def forum_manage_feedback(request):
    return HttpResponse("Staff forum: quản lý feedback")
