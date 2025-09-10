from authentication.models import Identity
from utils.service_base import ServiceBase


class IdentityService(ServiceBase[Identity]):
    manager = Identity.objects