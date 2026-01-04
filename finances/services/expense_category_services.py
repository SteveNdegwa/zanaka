from django.db import transaction
from django.core.exceptions import ValidationError

from base.services.base_services import BaseServices
from finances.models import ExpenseCategory
from schools.models import School
from users.models import User


class ExpenseCategoryServices(BaseServices):

    @classmethod
    def get_category(cls, category_id: str) -> ExpenseCategory:
        return ExpenseCategory.objects.get(id=category_id, is_active=True)

    @classmethod
    @transaction.atomic
    def create_category(cls, user: User, **data) -> ExpenseCategory:
        required_fields = {'name'}
        data = cls._sanitize_and_validate_data(data, required_fields=required_fields)

        if ExpenseCategory.objects.filter(name=data['name'], school=user.school, is_active=True).exists():
            raise ValidationError(f"Expense category with name '{data['name']}' already exists")

        category = ExpenseCategory.objects.create(
            school=user.school,
            name=data['name'],
            has_budget=data.get('has_budget', False),
            monthly_budget=data.get('monthly_budget'),
            annual_budget=data.get('annual_budget'),
            requires_approval=data.get('requires_approval', False),
        )
        return category

    @classmethod
    @transaction.atomic
    def update_category(cls, user: User, category_id: str, **data) -> ExpenseCategory:
        category = cls.get_category(category_id)

        update_fields = []

        if 'name' in data:
            if ExpenseCategory.objects.filter(
                    name=data['name'],
                    school=user.school,
                    is_active=True
            ).exclude(
                id=category_id
            ).exists():
                raise ValidationError(f"Expense category with name '{data['name']}' already exists")

            category.name = data['name']
            update_fields.append('name')

        if 'has_budget' in data:
            category.has_budget = data['has_budget']
            update_fields.append('has_budget')

        if 'monthly_budget' in data:
            category.monthly_budget = data['monthly_budget']
            update_fields.append('monthly_budget')

        if 'annual_budget' in data:
            category.annual_budget = data['annual_budget']
            update_fields.append('annual_budget')

        if 'requires_approval' in data:
            category.requires_approval = data['requires_approval']
            update_fields.append('requires_approval')

        if 'is_active' in data:
            category.is_active = data['is_active']
            update_fields.append('is_active')

        category.save(update_fields=update_fields)

        return category

    @classmethod
    @transaction.atomic
    def deactivate_category(cls, user: User, category_id: str) -> ExpenseCategory:
        category = cls.get_category(category_id)
        category.is_active = False
        category.save(update_fields=['is_active'])
        return category

    @classmethod
    @transaction.atomic
    def activate_category(cls, user: User, category_id: str) -> ExpenseCategory:
        category = cls.get_category(category_id)
        category.is_active = True
        category.save(update_fields=['is_active'])
        return category

    @classmethod
    def fetch_category(cls, category_id: str) -> dict:
        category = cls.get_category(category_id)
        return {
            'id': str(category.id),
            'name': category.name,
            'has_budget': category.has_budget,
            'monthly_budget': str(category.monthly_budget) if category.monthly_budget else None,
            'annual_budget': str(category.annual_budget) if category.annual_budget else None,
            'requires_approval': category.requires_approval,
            'is_active': category.is_active,
            'total_spent': category.get_total_spent(),
            'created_at': category.created_at.isoformat(),
            'updated_at': category.updated_at.isoformat(),
        }

    @classmethod
    def filter_categories(cls, school: School, **filters) -> list[dict]:
        qs = ExpenseCategory.objects.filter(school=school, is_active=True)

        search_term = filters.get('search_term')
        if search_term:
            qs = qs.filter(name__icontains=search_term)

        qs = qs.order_by('-created_at')
        return [cls.fetch_category(str(cat.id)) for cat in qs]