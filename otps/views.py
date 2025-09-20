import logging

from audit.decorators import set_activity_name
from base.views import BaseView
from otps.services.otp_service import OTPService
from utils.response_provider import ResponseProvider

logger = logging.getLogger(__name__)


class OTPView(BaseView):
    def post(self, request, action, *args, **kwargs):
        if action == 'send':
            return self.send_otp(request, *args, **kwargs)
        elif action == 'verify':
            return self.verify_otp(request, *args, **kwargs)
        return ResponseProvider.bad_request(message='Invalid action specified')

    @set_activity_name('Send OTP')
    def send_otp(self, request, *args, **kwargs):
        purpose = self.data.get('purpose', '')
        delivery_method = self.data.get('delivery_method', '')
        contact = self.data.get('contact', '')
        user_id = self.data.get('user_id', '')
        token = self.token

        OTPService.send_otp(
            purpose=purpose,
            delivery_method=delivery_method,
            contact=contact,
            user_id=user_id,
            token=token,
        )

        return ResponseProvider.success(message='OTP sent successfully')

    @set_activity_name('Verify OTP')
    def verify_otp(self, request, *args, **kwargs):
        purpose = self.data.get('purpose', '')
        code = self.data.get('code', '')
        contact = self.data.get('contact', '')
        user_id = self.data.get('user_id', '')
        token = self.token

        OTPService.verify_otp(
            purpose=purpose,
            code=code,
            contact=contact,
            user_id=user_id,
            token=token,
        )

        return ResponseProvider.success(message='OTP verified successfully')
