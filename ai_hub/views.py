from django.http import HttpResponse
from django.contrib.auth.decorators import permission_required

@permission_required("ai_hub.manage_ai_architecture", raise_exception=True)
def ai_arch_view(request):
    return HttpResponse("AI Architect only")
