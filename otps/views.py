import logging

from audit.context import RequestContext
from otps.backend.otp_management_service import OTPManagementService
from utils.response_provider import ResponseProvider

logger = logging.getLogger(__name__)


class OTPAPIHandler:
    @staticmethod
    def send_otp(request):
        """
        Sends a one-time password (OTP) to a user.

        :param request: Django HTTP request object containing 'purpose', 'delivery_method', 'contact', and
         optional 'user_id'.
        :type request: HttpRequest
        :return: JSON response with status code, message, and success status.
        :rtype: JsonResponse
        :raises Exception: On OTP sending failure.
        """
        try:
            data = RequestContext.data
            purpose = data.get('purpose', '')
            delivery_method = data.get('delivery_method', '')
            contact = data.get('contact', '')
            user_id = data.get('user_id', '')
            token = RequestContext.token

            OTPManagementService().send_otp(
                purpose=purpose,
                delivery_method=delivery_method,
                contact=contact,
                user_id=user_id,
                token=token
            )
            return ResponseProvider.success(message='OTP sent successfully')
        except Exception as ex:
            logger.exception('OTPAPIHandler - send_otp exception: %s', ex)
            return ResponseProvider.error(message='An error occurred while sending the OTP', error=str(ex))

    @staticmethod
    def verify_otp(request):
        """
        Verifies a one-time password (OTP) provided by the user.

        :param request: Django HTTP request object containing 'purpose', 'code', 'contact', and optional 'user_id'.
        :type request: HttpRequest
        :return: JSON response with status code, message, and success status.
        :rtype: JsonResponse
        :raises Exception: On OTP verification failure.
        """
        try:
            data = RequestContext.data
            purpose = data.get('purpose', '')
            code = data.get('code', '')
            contact = data.get('contact', '')
            user_id = data.get('user_id', '')
            token = RequestContext.token

            OTPManagementService().verify_otp(
                purpose=purpose,
                code=code,
                contact=contact,
                user_id=user_id,
                token=token
            )
            return ResponseProvider.success(message='OTP verified successfully')
        except Exception as ex:
            logger.exception('OTPAPIHandler - verify_otp exception: %s', ex)
            return ResponseProvider.error(message='An error occurred while verifying the OTP', error=str(ex))
