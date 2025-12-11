import logging
import requests

from typing import List, Dict

from notifications.services.providers.base_provider import BaseProvider
from notifications.models import NotificationStatus

logger = logging.getLogger(__name__)


class OnfonSMSProvider(BaseProvider):
    """
    SMS provider integration for the Onfon bulk messaging gateway.
    """

    def validate_config(self) -> bool:
        """
        Validate the provider configuration.

        :return: True if configuration is valid, otherwise False.
        :rtype: bool
        """
        required_keys = ["api_key", "client_id", "access_key", "url", "sender_id"]
        missing_keys = [key for key in required_keys if key not in self.config]

        if missing_keys:
            logger.error(
                "OnfonSMSProvider - Missing config keys: %s",
                ", ".join(missing_keys)
            )
            return False

        return True

    def send(self, recipients: List[str], content: Dict[str, str]) -> str:
        """
        Send an SMS message to one or more recipients.

        :param recipients: List of phone numbers to send the SMS to.
        :type recipients: List[str]
        :param content: Dictionary containing the message body.
        :type content: Dict[str, str]
        :return: NotificationStatus.SENT if sending is successful.
        :rtype: str
        :raises requests.HTTPError: If the HTTP request fails.
        :raises Exception: If the Onfon API returns a non-zero error code.
        """
        url = self.config.get("url")

        headers = {
            "AccessKey": self.config.get("access_key"),
            "Content-Type": "application/json"
        }

        data = {
            "SenderId": self.config.get("sender_id"),
            "IsUnicode": True,
            "IsFlash": False,
            "ScheduleDateTime": "",
            "MessageParameters": [
                {
                    "Number": recipient,
                    "Text": content.get("body", "")
                }
                for recipient in recipients
            ],
            "ApiKey": self.config.get("api_key"),
            "ClientId": self.config.get("client_id")
        }

        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()

        response_data = response.json()
        if response_data.get("ErrorCode") != 0:
            raise Exception(
                f"OnfonSMSProvider - API error: {response_data.get('ErrorMessage')}"
            )

        return NotificationStatus.SENT
