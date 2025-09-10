def get_client_ip(request):
    """
    Retrieve the client's IP address from a Django request object.

    :param request: Django HTTP request object.
    :type request: django.http.HttpRequest
    :return: The client IP address as a string, or None if not found.
    :rtype: str | None
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
       return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')