import datetime
from typing import Union, Optional

from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest

from users.models import User


class ExtendedRequest(HttpRequest):
    """
    Extends the base HttpRequest with additional attributes.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_client: Optional[str] = None
        self.token: Optional[str] = None
        self.user: Union[User, AnonymousUser] = AnonymousUser()
        self.is_authenticated: bool = False
        self.client_ip: Optional[str] = None
        self.user_agent: Optional[str] = None
        self.data: Optional[dict] = None
        self.file: Optional[dict] = None
        self.received_at: Optional[datetime.datetime] = None
