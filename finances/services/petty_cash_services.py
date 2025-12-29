from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, F

from base.services.base_services import BaseServices
from finances.models import PettyCash, PettyCashStatus, PettyCashTransaction
from users.models import User


class PettyCashServices(BaseServices):
    """
    Service layer for managing petty cash funds and transactions.
    """

    @classmethod
    def get_petty_cash_fund(cls, fund_id: str, select_for_update: bool = False) -> PettyCash:
        """
        Retrieve a single petty cash fund by ID.

        :param fund_id: ID of the fund to retrieve.
        :type fund_id: str
        :param select_for_update: If True, lock the row for update.
        :type select_for_update: bool
        :raises PettyCash.DoesNotExist: If the fund does not exist.
        :return: PettyCash instance.
        :rtype: PettyCash
        """
        qs = PettyCash.objects
        if select_for_update:
            qs = qs.select_for_update()
        return qs.get(id=fund_id)

    @classmethod
    @transaction.atomic
    def create_petty_cash_fund(cls, user: User, **data) -> PettyCash:
        """
        Create a new petty cash fund.

        :param user: User creating the fund.
        :type user: User
        :param data: Fund data including 'fund_name', 'custodian_id', 'initial_amount'.
        :type data: dict
        :raises ValidationError: If required fields are missing.
        :return: Created petty cash fund instance.
        :rtype: PettyCash
        """
        required_fields = {'fund_name', 'custodian_id', 'initial_amount'}
        field_types = {'initial_amount': float}
        data = cls._sanitize_and_validate_data(
            data,
            required_fields=required_fields,
            field_types=field_types
        )

        custodian = User.objects.get(id=data['custodian_id'])
        initial_amount = Decimal(str(data['initial_amount']))

        fund = PettyCash.objects.create(
            fund_name=data['fund_name'],
            custodian=custodian,
            initial_amount=initial_amount,
            current_balance=initial_amount,
            created_by=user
        )

        return fund

    @classmethod
    @transaction.atomic
    def replenish_petty_cash(cls, user: User, fund_id: str, amount: float, notes: str = "") -> PettyCash:
        """
        Replenish a petty cash fund.

        :param user: User performing the replenishment.
        :type user: User
        :param fund_id: ID of the fund to replenish.
        :type fund_id: str
        :param amount: Amount to add.
        :type amount: float
        :param notes: Optional notes.
        :type notes: str
        :return: Updated petty cash fund instance.
        :rtype: PettyCash
        """
        fund = cls.get_petty_cash_fund(fund_id, select_for_update=True)

        if fund.status != PettyCashStatus.ACTIVE:
            raise ValidationError('Can only replenish active petty cash funds')

        amount_decimal = Decimal(str(amount))
        fund.replenish(amount_decimal, user, notes)

        return fund

    @classmethod
    @transaction.atomic
    def close_petty_cash_fund(cls, user: User, fund_id: str) -> PettyCash:
        """
        Close a petty cash fund.

        :param user: User closing the fund.
        :type user: User
        :param fund_id: ID of the fund to close.
        :type fund_id: str
        :return: Closed petty cash fund instance.
        :rtype: PettyCash
        """
        fund = cls.get_petty_cash_fund(fund_id, select_for_update=True)
        fund.status = PettyCashStatus.CLOSED
        fund.updated_by = user
        fund.save(update_fields=['status', 'updated_by'])
        return fund

    @classmethod
    @transaction.atomic
    def reopen_petty_cash_fund(cls, user: User, fund_id: str) -> PettyCash:
        """
        Reopen a closed petty cash fund.

        :param user: User reopening the fund.
        :type user: User
        :param fund_id: ID of the fund to reopen.
        :type fund_id: str
        :return: Reopened petty cash fund instance.
        :rtype: PettyCash
        """
        fund = cls.get_petty_cash_fund(fund_id, select_for_update=True)

        if fund.status != PettyCashStatus.CLOSED:
            raise ValidationError('Only closed funds can be reopened')

        fund.status = PettyCashStatus.ACTIVE
        fund.updated_by = user
        fund.save(update_fields=['status', 'updated_by'])
        return fund

    @classmethod
    def fetch_petty_cash_fund(cls, fund_id: str) -> dict:
        """
        Retrieve petty cash fund details with recent transactions.

        :param fund_id: ID of the fund to fetch.
        :type fund_id: str
        :return: Dictionary with fund details and recent transactions.
        :rtype: dict
        """
        fund = cls.get_petty_cash_fund(fund_id)

        recent_transactions = list(
            PettyCashTransaction.objects
            .filter(petty_cash_fund=fund)
            .order_by("""-created_at""")[:10]
            .values(
                'id', 'description', 'transaction_type', 'amount',
                'balance_before', 'balance_after', 'processed_by_id',
                'expense_id', 'notes', 'created_at'
            )
        )

        return {
            'id': str(fund.id),
            'fund_name': fund.fund_name,
            'custodian_id': str(fund.custodian.id),
            'custodian_full_name': fund.custodian.full_name,
            'initial_amount': fund.initial_amount,
            'current_balance': fund.current_balance,
            'status': fund.status,
            'created_at': fund.created_at,
            'updated_at': fund.updated_at,
            'recent_transactions': recent_transactions
        }

    @classmethod
    def filter_petty_cash_funds(cls, **filters) -> list[dict]:
        """
        Filter petty cash funds based on fields and search term.

        :param filters: Keyword arguments containing fund fields and optional 'search_term'.
        :type filters: dict
        :return: List of fund dictionaries matching filters.
        :rtype: list[dict]
        """
        filters = cls._sanitize_and_validate_data(filters)

        fund_field_names = {f.name for f in PettyCash._meta.get_fields()}
        cleaned_filters = {k: v for k, v in filters.items() if k in fund_field_names}

        qs = PettyCash.objects.filter(**cleaned_filters).order_by('-created_at')

        search_term = filters.get('search_term')
        if search_term:
            fields = ['fund_name', 'custodian__first_name', 'custodian__last_name']
            search_q = Q()
            for field in fields:
                search_q |= Q(**{f'{field}__icontains': search_term})
            qs = qs.filter(search_q)

        fund_ids = qs.values_list('id', flat=True)
        return [cls.fetch_petty_cash_fund(fund_id) for fund_id in fund_ids]

    @classmethod
    def fetch_petty_cash_transactions(cls, fund_id: str, **filters) -> list[dict]:
        """
        Retrieve petty cash transactions for a specific fund.

        :param fund_id: ID of the fund.
        :type fund_id: str
        :param filters: Optional filters like start_date, end_date, transaction_type.
        :type filters: dict
        :return: List of transaction dictionaries.
        :rtype: list[dict]
        """
        fund = cls.get_petty_cash_fund(fund_id)

        qs = PettyCashTransaction.objects.filter(petty_cash_fund=fund)

        if filters.get('start_date'):
            qs = qs.filter(created_at__gte=filters['start_date'])
        if filters.get('end_date'):
            qs = qs.filter(created_at__lte=filters['end_date'])
        if filters.get('transaction_type'):
            qs = qs.filter(transaction_type=filters['transaction_type'])

        transactions = qs.annotate(
            processed_by_full_name=F('processed_by__full_name'),
            expense_reference=F('expense__expense_reference')
        ).values(
            'id', 'description', 'transaction_type', 'amount',
            'balance_before', 'balance_after', 'processed_by_id',
            'processed_by_full_name', 'expense_id', 'expense_reference',
            'notes', 'created_at'
        )

        return list(transactions)
