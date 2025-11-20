from notifications.services.providers.belio_sms_provider import BelioSMSProvider
from notifications.services.providers.gmail_smtp_server import GmailSMTPServer
from notifications.services.providers.onfon_sms_provider import OnfonSMSProvider

PROVIDER_CLASSES = {
    "GmailSMTPServer": GmailSMTPServer,
    "BelioSMSProvider": BelioSMSProvider,
    "OnfonSMSProvider": OnfonSMSProvider,
}