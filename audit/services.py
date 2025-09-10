from audit.models import AuditLog, AuditConfiguration, RequestLog
from utils.service_base import ServiceBase


class RequestLogService(ServiceBase[RequestLog]):
    manager = RequestLog.objects


class AuditLogService(ServiceBase):
    manager = AuditLog.objects


class AuditConfigurationService(ServiceBase):
    manager = AuditConfiguration.objects