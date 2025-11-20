import logging
import requests

from typing import List, Dict

from notifications.services.providers.base_provider import BaseProvider
from notifications.models import NotificationStatus

logger = logging.getLogger(__name__)


class OnfonSMSProvider(BaseProvider):
    def validate_config(self) -> bool:
        required_keys = ["api_key", "client_id", "access_key", "url", "sender_id"]
        missing_keys = [key for key in required_keys if key not in self.config]
        if missing_keys:
            logger.error("OnfonSMSProvider - Missing config keys: %s", ", ".join(missing_keys))
            return False
        return True

    def send(self, recipients: List[str], content: Dict[str, str]) -> str:
        url = self.config.get('url')

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
                    "Text": content.get("body", ""),
                }
                for recipient in recipients
            ],
            "ApiKey": self.config.get("api_key"),
            "ClientId": self.config.get("client_id"),

        }

        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        response_data = response.json()

        if response_data.get("ErrorCode") != 0:
            raise Exception(f"OnfonSMSProvider - API error: {response_data.get('ErrorMessage')}")

        return NotificationStatus.SENT
