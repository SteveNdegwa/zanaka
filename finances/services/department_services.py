from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Sum, Q
from django.utils import timezone

from base.services.base_services import BaseServices
from finances.models import Department, Expense, ExpenseStatus
from users.models import User


class DepartmentServices(BaseServices):
    """
    Service layer for managing departments.
    """

    @classmethod
    def get_department(cls, department_id: str, select_for_update: bool = False) -> Department:
        """
        Retrieve a single department by ID.

        :param department_id: ID of the department to retrieve.
        :type department_id: str
        :param select_for_update: If True, lock the row for update.
        :type select_for_update: bool
        :raises Department.DoesNotExist: If the department does not exist.
        :return: Department instance.
        :rtype: Department
        """
        qs = Department.objects
        if select_for_update:
            qs = qs.select_for_update()
        return qs.get(id=department_id)

    @classmethod
    @transaction.atomic
    def create_department(cls, user: User, **data) -> Department:
        """
        Create a new department.

        :param user: User creating the department.
        :type user: User
        :param data: Department data including 'name', 'head_id', 'budget_allocated'.
        :type data: dict
        :raises ValidationError: If required fields are missing.
        :return: Created department instance.
        :rtype: Department
        """
        required_fields = {"name"}
        field_types = {"budget_allocated": float}
        data = cls._sanitize_and_validate_data(
            data,
            required_fields=required_fields,
            field_types=field_types
        )

        head = None
        if data.get("head_id"):
            head = User.objects.get(id=data["head_id"])

        budget_allocated = Decimal("0.00")
        if data.get("budget_allocated"):
            budget_allocated = Decimal(str(data["budget_allocated"]))

        department = Department.objects.create(
            name=data["name"],
            head=head,
            budget_allocated=budget_allocated,
            created_by=user
        )

        return department

    @classmethod
    @transaction.atomic
    def update_department(cls, user: User, department_id: str, **data) -> Department:
        """
        Update an existing department.

        :param user: User performing the update.
        :type user: User
        :param department_id: ID of the department to update.
        :type department_id: str
        :param data: Updated department data.
        :type data: dict
        :return: Updated department instance.
        :rtype: Department
        """
        department = cls.get_department(department_id, select_for_update=True)

        field_types = {"budget_allocated": float}
        data = cls._sanitize_and_validate_data(data, field_types=field_types)

        update_fields = ["updated_by"]

        if "name" in data:
            department.name = data["name"]
            update_fields.append("name")

        if "head_id" in data:
            department.head = User.objects.get(id=data["head_id"]) if data["head_id"] else None
            update_fields.append("head")

        if "budget_allocated" in data:
            department.budget_allocated = Decimal(str(data["budget_allocated"]))
            update_fields.append("budget_allocated")

        department.updated_by = user
        department.save(update_fields=update_fields)

        return department

    @classmethod
    @transaction.atomic
    def deactivate_department(cls, user: User, department_id: str) -> Department:
        """
        Deactivate a department.

        :param user: User performing the deactivation.
        :type user: User
        :param department_id: ID of the department to deactivate.
        :type department_id: str
        :return: Deactivated department instance.
        :rtype: Department
        """
        department = cls.get_department(department_id, select_for_update=True)
        department.is_active = False
        department.updated_by = user
        department.save(update_fields=["is_active", "updated_by"])
        return department

    @classmethod
    @transaction.atomic
    def activate_department(cls, user: User, department_id: str) -> Department:
        """
        Activate a department.

        :param user: User performing the activation.
        :type user: User
        :param department_id: ID of the department to activate.
        :type department_id: str
        :return: Activated department instance.
        :rtype: Department
        """
        department = cls.get_department(department_id, select_for_update=True)
        department.is_active = True
        department.updated_by = user
        department.save(update_fields=["is_active", "updated_by"])
        return department

    @classmethod
    def fetch_department(cls, department_id: str) -> dict:
        """
        Retrieve department details with expense statistics.

        :param department_id: ID of the department to fetch.
        :type department_id: str
        :return: Dictionary with department details.
        :rtype: dict
        """
        department = cls.get_department(department_id)

        # Get current year stats
        current_year_start = timezone.now().replace(month=1, day=1).date()
        current_year_expenses = department.get_total_expenses(start_date=current_year_start)
        budget_utilization = department.get_budget_utilization()

        return {
            "id": str(department.id),
            "name": department.name,
            "head_id": str(department.head.id) if department.head else None,
            "head_full_name": department.head.full_name if department.head else None,
            "budget_allocated": department.budget_allocated,
            "current_year_expenses": current_year_expenses,
            "budget_utilization_percentage": round(budget_utilization, 2),
            "remaining_budget": department.budget_allocated - current_year_expenses,
            "all_time_expenses": department.get_total_expenses(),
            "is_active": department.is_active,
            "created_at": department.created_at,
            "updated_at": department.updated_at,
        }

    @classmethod
    def filter_departments(cls, **filters) -> list[dict]:
        """
        Filter departments based on fields and search term.

        :param filters: Keyword arguments containing department fields and optional 'search_term'.
        :type filters: dict
        :return: List of department dictionaries matching filters.
        :rtype: list[dict]
        """
        filters = cls._sanitize_and_validate_data(filters)

        department_field_names = set(Department._meta.fields_map.keys())
        cleaned_filters = {k: v for k, v in filters.items() if k in department_field_names}

        qs = Department.objects.filter(**cleaned_filters)

        search_term = filters.get("search_term")
        if search_term:
            fields = ["name", "code", "head__first_name", "head__last_name"]
            search_q = Q()
            for field in fields:
                search_q |= Q(**{f"{field}__icontains": search_term})
            qs = qs.filter(search_q)

        department_ids = qs.values_list("id", flat=True)
        return [cls.fetch_department(department_id) for department_id in department_ids]

    @classmethod
    def get_department_expense_breakdown(cls, department_id: str, **filters) -> dict:
        """
        Get detailed expense breakdown for a department by category.

        :param department_id: ID of the department.
        :type department_id: str
        :param filters: Optional filters like start_date, end_date.
        :type filters: dict
        :return: Dictionary with expense breakdown by category.
        :rtype: dict
        """
        department = cls.get_department(department_id)

        qs = Expense.objects.filter(
            department=department,
            status=ExpenseStatus.APPROVED
        )

        if filters.get("start_date"):
            qs = qs.filter(expense_date__gte=filters["start_date"])
        if filters.get("end_date"):
            qs = qs.filter(expense_date__lte=filters["end_date"])

        # Breakdown by category
        category_breakdown = qs.values(
            "category__name", "category__id"
        ).annotate(
            total_amount=Sum("amount"),
            expense_count=Count("id")
        ).order_by("-total_amount")

        # Breakdown by payment method
        payment_method_breakdown = qs.values("payment_method").annotate(
            total_amount=Sum("amount"),
            expense_count=Count("id")
        )

        # Monthly trend
        monthly_trend = qs.values(
            "expense_date__year", "expense_date__month"
        ).annotate(
            total_amount=Sum("amount"),
            expense_count=Count("id")
        ).order_by("expense_date__year", "expense_date__month")

        total_expenses = qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        return {
            "department_id": str(department.id),
            "department_name": department.name,
            "total_expenses": total_expenses,
            "budget_allocated": department.budget_allocated,
            "budget_remaining": department.budget_allocated - total_expenses,
            "category_breakdown": list(category_breakdown),
            "payment_method_breakdown": list(payment_method_breakdown),
            "monthly_trend": list(monthly_trend),
        }