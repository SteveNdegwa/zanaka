from django.http import JsonResponse

from otps.services.otp_services import OTPServices
from utils.extended_request import ExtendedRequest
from utils.response_provider import ResponseProvider


def send_otp(request: ExtendedRequest) -> JsonResponse:
    purpose = request.data.get('purpose','')
    delivery_method = request.data.get('delivery_method','')
    contact = request.data.get('contact','')
    user = request.user if request.user.is_authenticated else None
    token = getattr(request, 'token', None)

    OTPServices.send_otp(
        purpose=purpose,
        delivery_method=delivery_method,
        contact=contact,
        user=user,
        token=token,
    )

    return ResponseProvider.success(
        message='OTP sent successfully'
    )


def verify_otp(request: ExtendedRequest) -> JsonResponse:
    purpose = request.data.get('purpose','')
    code = request.data.get('code','')
    contact = request.data.get('contact','')
    user = request.user if request.user.is_authenticated else None
    token = getattr(request, 'token', None)

    data = OTPServices.verify_otp(
        purpose=purpose,
        code=code,
        contact=contact,
        user=user,
        token=token,
    )

    return ResponseProvider.success(
        message='OTP verified successfully',
        data=data
    )
