from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from base.services.base_services import BaseServices
from finances.models import Vendor
from users.models import User


class VendorServices(BaseServices):
    """
    Service layer for managing vendors.
    """

    @classmethod
    def get_vendor(cls, vendor_id: str, select_for_update: bool = False) -> Vendor:
        """
        Retrieve a single vendor by ID.

        :param vendor_id: ID of the vendor to retrieve.
        :type vendor_id: str
        :param select_for_update: If True, lock the row for update.
        :type select_for_update: bool
        :raises Vendor.DoesNotExist: If the vendor does not exist.
        :return: Vendor instance.
        :rtype: Vendor
        """
        qs = Vendor.objects
        if select_for_update:
            qs = qs.select_for_update()
        return qs.get(id=vendor_id)

    @classmethod
    @transaction.atomic
    def create_vendor(cls, user: User, **data) -> Vendor:
        """
        Create a new vendor.

        :param user: User creating the vendor.
        :type user: User
        :param data: Vendor data.
        :type data: dict
        :raises ValidationError: If required fields are missing.
        :return: Created vendor instance.
        :rtype: Vendor
        """
        required_fields = {'name'}
        data = cls._sanitize_and_validate_data(data, required_fields=required_fields)

        vendor = Vendor.objects.create(
            name=data['name'],
            school=user.school,
            contact_person=data.get('contact_person', ''),
            email=data.get('email', ''),
            phone=data.get('phone', ''),
            address=data.get('address', ''),
            kra_pin=data.get('kra_pin', ''),
            payment_terms=data.get('payment_terms', 'net_30'),
            mpesa_pochi_number=data.get('mpesa_pochi_number', ''),
            mpesa_paybill_number=data.get('mpesa_paybill_number', ''),
            mpesa_paybill_account=data.get('mpesa_paybill_account', ''),
            mpesa_till_number=data.get('mpesa_till_number', ''),
            bank_name=data.get('bank_name', ''),
            bank_account=data.get('bank_account', ''),
            bank_branch=data.get('bank_branch', ''),
            notes=data.get('notes', ''),
        )

        return vendor

    @classmethod
    @transaction.atomic
    def update_vendor(cls, user: User, vendor_id: str, **data) -> Vendor:
        """
        Update an existing vendor.

        :param user: User performing the update.
        :type user: User
        :param vendor_id: ID of the vendor to update.
        :type vendor_id: str
        :param data: Updated vendor data.
        :type data: dict
        :return: Updated vendor instance.
        :rtype: Vendor
        """
        vendor = cls.get_vendor(vendor_id, select_for_update=True)

        update_fields = []

        if 'name' in data:
            vendor.name = data['name']
            update_fields.append('name')

        if 'contact_person' in data:
            vendor.contact_person = data['contact_person']
            update_fields.append('contact_person')

        if 'email' in data:
            vendor.email = data['email']
            update_fields.append('email')

        if 'phone' in data:
            vendor.phone = data['phone']
            update_fields.append('phone')

        if 'address' in data:
            vendor.address = data['address']
            update_fields.append('address')

        if 'kra_pin' in data:
            print("here")
            vendor.kra_pin = data['kra_pin']
            update_fields.append('kra_pin')

        if 'payment_terms' in data:
            vendor.payment_terms = data['payment_terms']
            update_fields.append('payment_terms')

        if 'mpesa_pochi_number' in data:
            vendor.mpesa_pochi_number = data['mpesa_pochi_number']
            update_fields.append('mpesa_pochi_number')

        if 'mpesa_paybill_number' in data:
            vendor.mpesa_paybill_number = data['mpesa_paybill_number']
            update_fields.append('mpesa_paybill_number')

        if 'mpesa_paybill_account' in data:
            vendor.mpesa_paybill_account = data['mpesa_paybill_account']
            update_fields.append('mpesa_paybill_account')

        if 'mpesa_till_number' in data:
            vendor.mpesa_till_number = data['mpesa_till_number']
            update_fields.append('mpesa_till_number')

        if 'bank_name' in data:
            vendor.bank_name = data['bank_name']
            update_fields.append('bank_name')

        if 'bank_account' in data:
            vendor.bank_account = data['bank_account']
            update_fields.append('bank_account')

        if 'bank_branch' in data:
            vendor.bank_branch = data['bank_branch']
            update_fields.append('bank_branch')

        if 'notes' in data:
            vendor.notes = data['notes']
            update_fields.append('notes')

        vendor.save(update_fields=update_fields)

        return vendor

    @classmethod
    @transaction.atomic
    def deactivate_vendor(cls, user: User, vendor_id: str) -> Vendor:
        """
        Deactivate a vendor.

        :param user: User performing the deactivation.
        :type user: User
        :param vendor_id: ID of the vendor to deactivate.
        :type vendor_id: str
        :return: Deactivated vendor instance.
        :rtype: Vendor
        """
        vendor = cls.get_vendor(vendor_id, select_for_update=True)
        vendor.is_active = False
        vendor.save(update_fields=['is_active'])
        return vendor

    @classmethod
    @transaction.atomic
    def activate_vendor(cls, user: User, vendor_id: str) -> Vendor:
        """
        Activate a vendor.

        :param user: User performing the activation.
        :type user: User
        :param vendor_id: ID of the vendor to activate.
        :type vendor_id: str
        :return: Activated vendor instance.
        :rtype: Vendor
        """
        vendor = cls.get_vendor(vendor_id, select_for_update=True)
        vendor.is_active = True
        vendor.updated_by = user
        vendor.save(update_fields=['is_active', 'updated_by'])
        return vendor

    @classmethod
    def fetch_vendor(cls, vendor_id: str) -> dict:
        """
        Retrieve vendor details with total paid amounts.

        :param vendor_id: ID of the vendor to fetch.
        :type vendor_id: str
        :return: Dictionary with vendor details.
        :rtype: dict
        """
        vendor = cls.get_vendor(vendor_id)
        current_year = timezone.now().year

        return {
            'id': str(vendor.id),
            'name': vendor.name,
            'contact_person': vendor.contact_person,
            'email': vendor.email,
            'phone': vendor.phone,
            'address': vendor.address,
            'kra_pin': vendor.kra_pin,
            'payment_terms': vendor.payment_terms,
            'mpesa_pochi_number': vendor.mpesa_pochi_number,
            'mpesa_paybill_number': vendor.mpesa_paybill_number,
            'mpesa_paybill_account': vendor.mpesa_paybill_account,
            'mpesa_till_number': vendor.mpesa_till_number,
            'bank_name': vendor.bank_name,
            'bank_account': vendor.bank_account,
            'bank_branch': vendor.bank_branch,
            'is_active': vendor.is_active,
            'notes': vendor.notes,
            'total_paid_current_year': vendor.get_total_paid(year=current_year),
            'total_paid_all_time': vendor.get_total_paid(),
            'created_at': vendor.created_at,
            'updated_at': vendor.updated_at,
        }

    @classmethod
    def filter_vendors(cls, **filters) -> list[dict]:
        """
        Filter vendors based on fields and search term.

        :param filters: Keyword arguments containing vendor fields and optional 'search_term'.
        :type filters: dict
        :return: List of vendor dictionaries matching filters.
        :rtype: list[dict]
        """
        filters = cls._sanitize_and_validate_data(filters)

        vendor_field_names = {f.name for f in Vendor._meta.get_fields()}
        cleaned_filters = {k: v for k, v in filters.items() if k in vendor_field_names}

        qs = Vendor.objects.filter(is_active=True, **cleaned_filters).order_by('-created_at')

        search_term = filters.get('search_term')
        if search_term:
            fields = ['name', 'contact_person', 'email', 'phone', 'tax_id', 'code']
            search_q = Q()
            for field in fields:
                search_q |= Q(**{f'{field}__icontains': search_term})
            qs = qs.filter(search_q)

        vendor_ids = qs.values_list('id', flat=True)
        return [cls.fetch_vendor(vendor_id) for vendor_id in vendor_ids]
