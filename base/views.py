import logging
from django.views import View
from utils.response_provider import ResponseProvider
from audit.context import RequestContext

logger = logging.getLogger(__name__)

class BaseView(View):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        self.user = RequestContext.user
        self.data = RequestContext.data
        self.token = RequestContext.token

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except Exception as ex:
            logger.exception(
                "Unhandled exception in %s %s: %s",
                request.method, request.path, ex
            )
            return ResponseProvider.handle_exception(ex)