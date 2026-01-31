from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def health_check(request):
    """
    Simple health check endpoint.
    Returns HTTP 200 with status OK.
    """
    return JsonResponse({"status": "ok"})

