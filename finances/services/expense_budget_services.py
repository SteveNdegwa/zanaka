from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from base.services.base_services import BaseServices
from finances.models import ExpenseBudget, ExpenseCategory, Department
from users.models import User


class ExpenseBudgetServices(BaseServices):
    """
    Service layer for managing expense budgets and viewing utilization.
    """

    @classmethod
    def get_expense_budget(cls, budget_id: str, select_for_update: bool = False) -> ExpenseBudget:
        """
        Retrieve a single expense budget by ID.

        :param budget_id: ID of the budget to retrieve.
        :type budget_id: str
        :param select_for_update: If True, lock the row for update.
        :type select_for_update: bool
        :raises ExpenseBudget.DoesNotExist: If the budget does not exist.
        :return: ExpenseBudget instance.
        :rtype: ExpenseBudget
        """
        qs = ExpenseBudget.objects
        if select_for_update:
            qs = qs.select_for_update()
        return qs.get(id=budget_id, is_active=True)

    @classmethod
    @transaction.atomic
    def create_expense_budget(cls, user: User, **data) -> ExpenseBudget:
        """
        Create a new expense budget.

        :param user: User creating the budget.
        :type user: User
        :param data: Budget data including 'fiscal_year', 'category_id', 'budget_amount', etc.
        :type data: dict
        :raises ValidationError: If required fields are missing or dates are invalid.
        :return: Created expense budget instance.
        :rtype: ExpenseBudget
        """
        required_fields = {'fiscal_year', 'category_id', 'budget_amount', 'start_date', 'end_date'}
        field_types = {'budget_amount': float}
        data = cls._sanitize_and_validate_data(
            data,
            required_fields=required_fields,
            field_types=field_types
        )

        category = ExpenseCategory.objects.get(id=data['category_id'], is_active=True)

        department = None
        if data.get('department_id'):
            department = Department.objects.get(id=data['department_id'], is_active=True)

        # Validate dates
        start_date = data['start_date']
        end_date = data['end_date']
        if end_date <= start_date:
            raise ValidationError('End date must be after start date')

        budget = ExpenseBudget.objects.create(
            fiscal_year=data['fiscal_year'],
            category=category,
            department=department,
            budget_amount=Decimal(str(data['budget_amount'])),
            period=data.get('period', 'annual'),
            start_date=start_date,
            end_date=end_date,
            notes=data.get('notes', ''),
            created_by=user
        )

        return budget

    @classmethod
    @transaction.atomic
    def update_expense_budget(cls, user: User, budget_id: str, **data) -> ExpenseBudget:
        """
        Update an existing expense budget.

        :param user: User performing the update.
        :type user: User
        :param budget_id: ID of the budget to update.
        :type budget_id: str
        :param data: Updated budget data.
        :type data: dict
        :return: Updated expense budget instance.
        :rtype: ExpenseBudget
        """
        budget = cls.get_expense_budget(budget_id, select_for_update=True)

        field_types = {'budget_amount': float}
        data = cls._sanitize_and_validate_data(data, field_types=field_types)

        update_fields = ['updated_by']

        if 'budget_amount' in data:
            budget.budget_amount = Decimal(str(data['budget_amount']))
            update_fields.append('budget_amount')

        if 'start_date' in data:
            budget.start_date = data['start_date']
            update_fields.append('start_date')

        if 'end_date' in data:
            budget.end_date = data['end_date']
            update_fields.append('end_date')

        if 'notes' in data:
            budget.notes = data['notes']
            update_fields.append('notes')

        # Validate dates if either changed
        if 'start_date' in data or 'end_date' in data:
            if budget.end_date <= budget.start_date:
                raise ValidationError('End date must be after start date')

        budget.updated_by = user
        budget.save(update_fields=update_fields)

        return budget

    @classmethod
    @transaction.atomic
    def delete_expense_budget(cls, user: User, budget_id: str) -> None:
        """
        Delete an expense budget.

        :param user: User performing the deletion.
        :type user: User
        :param budget_id: ID of the budget to delete.
        :type budget_id: str
        """
        budget = cls.get_expense_budget(budget_id, select_for_update=True)
        budget.is_active = False
        budget.updated_by = user
        budget.save(update_fields=['is_active', 'updated_by'])

    @classmethod
    def fetch_expense_budget(cls, budget_id: str) -> dict:
        """
        Retrieve expense budget details with utilization metrics.

        :param budget_id: ID of the budget to fetch.
        :type budget_id: str
        :return: Dictionary with budget details and utilization.
        :rtype: dict
        """
        budget = cls.get_expense_budget(budget_id)

        spent_amount = budget.get_spent_amount()
        utilization_percentage = budget.get_utilization_percentage()
        remaining_budget = budget.get_remaining_budget()

        return {
            'id': str(budget.id),
            'fiscal_year': budget.fiscal_year,
            'category_id': str(budget.category.id),
            'category_name': budget.category.name,
            'department_id': str(budget.department.id) if budget.department else None,
            'department_name': budget.department.name if budget.department else None,
            'budget_amount': budget.budget_amount,
            'spent_amount': spent_amount,
            'remaining_budget': remaining_budget,
            'utilization_percentage': round(utilization_percentage, 2),
            'period': budget.period,
            'start_date': budget.start_date,
            'end_date': budget.end_date,
            'notes': budget.notes,
            'created_by_id': str(budget.created_by.id),
            'created_by_full_name': budget.created_by.full_name,
            'created_at': budget.created_at,
            'updated_at': budget.updated_at,
        }

    @classmethod
    def filter_expense_budgets(cls, **filters) -> list[dict]:
        """
        Filter expense budgets based on fields.

        :param filters: Keyword arguments containing budget fields.
        :type filters: dict
        :return: List of budget dictionaries matching filters.
        :rtype: list[dict]
        """
        filters = cls._sanitize_and_validate_data(filters)

        budget_field_names = {f.name for f in ExpenseBudget._meta.get_fields()}
        cleaned_filters = {k: v for k, v in filters.items() if k in budget_field_names}

        qs = ExpenseBudget.objects.filter(**cleaned_filters).order_by('-created_at')

        budget_ids = qs.values_list('id', flat=True)
        return [cls.fetch_expense_budget(budget_id) for budget_id in budget_ids]

    @classmethod
    def get_budget_utilization_report(cls, **filters) -> list[dict]:
        """
        Get a comprehensive budget utilization report.

        :param filters: Optional filters like fiscal_year, department_id, category_id.
        :type filters: dict
        :return: List of budget utilization data.
        :rtype: list[dict]
        """
        qs = ExpenseBudget.objects.filter(is_active=True)

        if filters.get('fiscal_year'):
            qs = qs.filter(fiscal_year=filters['fiscal_year'])
        if filters.get('department_id'):
            qs = qs.filter(department_id=filters['department_id'])
        if filters.get('category_id'):
            qs = qs.filter(category_id=filters['category_id'])

        report = []
        for budget in qs:
            spent_amount = budget.get_spent_amount()
            utilization_percentage = budget.get_utilization_percentage()
            remaining_budget = budget.get_remaining_budget()

            status = 'under_budget'
            if utilization_percentage >= 100:
                status = 'over_budget'
            elif utilization_percentage >= 80:
                status = 'near_limit'

            report.append({
                'budget_id': str(budget.id),
                'fiscal_year': budget.fiscal_year,
                'category_name': budget.category.name(),
                'department_name': budget.department.name if budget.department else 'All Departments',
                'budget_amount': budget.budget_amount,
                'spent_amount': spent_amount,
                'remaining_budget': remaining_budget,
                'utilization_percentage': round(utilization_percentage, 2),
                'status': status,
                'period': budget.period,
                'start_date': budget.start_date,
                'end_date': budget.end_date,
            })

        return report