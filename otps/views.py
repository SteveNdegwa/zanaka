from otps.services.otp_services import OTPServices
from utils.response_provider import ResponseProvider


def send_otp(request):
    purpose = request.data.get("purpose","")
    delivery_method = request.data.get("delivery_method","")
    contact = request.data.get("contact","")
    user_id = request.data.get("user_id","")
    token = getattr(request, "token", None)

    OTPServices.send_otp(
        purpose=purpose,
        delivery_method=delivery_method,
        contact=contact,
        user_id=user_id,
        token=token,
    )

    return ResponseProvider.success(
        message="OTP sent successfully"
    )


def verify_otp(request):
    purpose = request.data.get("purpose","")
    code = request.data.get("code","")
    contact = request.data.get("contact","")
    user_id = request.data.get("user_id","")
    token = getattr(request, "token", None)

    OTPServices.verify_otp(
        purpose=purpose,
        code=code,
        contact=contact,
        user_id=user_id,
        token=token,
    )

    return ResponseProvider.success(
        message="OTP verified successfully"
    )
