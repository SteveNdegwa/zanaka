from django.db import models


class InvoiceManager(models.Manager):
    def get(self, *args, **kwargs):
        from finances.models import Invoice
        obj = super().get(*args, **kwargs)
        new_status = obj.computed_status
        if new_status != obj.status:
            obj.status = new_status
            super(Invoice, obj).save()
        return obj
