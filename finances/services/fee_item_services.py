from typing import Optional, List
from decimal import Decimal

from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.db.models import Q

from base.services.base_services import BaseServices
from finances.models import (
    FeeItem, FeeItemCategory, GradeLevelFee, GradeLevel, Term
)
from schools.models import Branch
from users.models import User


class FeeItemServices(BaseServices):
    """
    Service layer for managing fee items, including creation, update,
    deactivation, fetching, and filtering.
    """

    fk_mappings = {}  # No foreign keys to other apps needing special handling here

    @classmethod
    def get_fee_item(
        cls,
        fee_item_id: str,
        select_for_update: bool = False
    ) -> FeeItem:
        """
        Retrieve a single fee item by ID, optionally filtering by active status.

        :param fee_item_id: ID of the fee item to retrieve.
        :param select_for_update: Lock row for update if True.
        :return: FeeItem instance.
        """
        filters = Q(id=fee_item_id, is_active=True)
        qs = FeeItem.objects
        if select_for_update:
            qs = qs.select_for_update()

        return qs.get(filters)

    @classmethod
    @transaction.atomic
    def create_fee_item(cls, user: User, **data) -> FeeItem:
        """
        Create a new fee item.

        :param user: User creating the fee item.
        :param data: Fee item data.
        :return: Created FeeItem instance.
        """
        required_fields = {'name', 'default_amount', 'category'}
        field_types = {
            'default_amount': float,
            'is_active': bool
        }

        data = cls._sanitize_and_validate_data(
            data,
            required_fields=required_fields,
            field_types=field_types
        )

        fee_item = FeeItem.objects.create(
            school=user.school,
            name=data['name'],
            default_amount=Decimal(str(data['default_amount'])),
            category=data['category'],
            is_active=data.get('is_active', True),
            description=data.get('description', '')
        )

        branch_ids = data.get('branch_ids', [])
        if branch_ids:
            branches = Branch.objects.filter(id__in=branch_ids, school=user.school)
            fee_item.branches.set(branches)

        return fee_item

    @classmethod
    @transaction.atomic
    def update_fee_item(cls, user: User, fee_item_id: str, **data) -> FeeItem:
        """
        Update an existing fee item.

        :param user: User performing the update.
        :param fee_item_id: ID of the fee item.
        :param data: Updated data.
        :return: Updated FeeItem instance.
        """
        fee_item = cls.get_fee_item(fee_item_id, select_for_update=True)

        if user.school != fee_item.school and not user.is_superuser:
            raise PermissionDenied("You can only update fee items in your school")

        field_types = {
            'default_amount': float,
            'is_active': bool
        }
        data = cls._sanitize_and_validate_data(data, field_types=field_types)

        update_fields = []

        if 'name' in data:
            fee_item.name = data['name']
            update_fields.append('name')

        if 'default_amount' in data:
            fee_item.default_amount = Decimal(str(data['default_amount']))
            update_fields.append('default_amount')

        if 'category' in data:
            if data['category'] not in dict(FeeItemCategory.choices):
                raise ValidationError(f"Invalid category: {data['category']}")
            fee_item.category = data['category']
            update_fields.append('category')

        if 'description' in data:
            fee_item.description = data['description']
            update_fields.append('description')

        if 'is_active' in data:
            fee_item.is_active = data['is_active']
            update_fields.append('is_active')

        if 'branch_ids' in data:
            branch_ids = data['branch_ids']
            if branch_ids:
                branches = Branch.objects.filter(id__in=branch_ids, school=fee_item.school)
                fee_item.branches.set(branches)
            else:
                fee_item.branches.clear()

        if update_fields:
            fee_item.save(update_fields=update_fields)

        return fee_item

    @classmethod
    @transaction.atomic
    def deactivate_fee_item(cls, user: User, fee_item_id: str) -> FeeItem:
        """
        Deactivate (soft delete) a fee item.

        :param user: User performing deactivation.
        :param fee_item_id: ID of the fee item.
        :return: Deactivated FeeItem instance.
        """
        fee_item = cls.get_fee_item(fee_item_id, is_active=True, select_for_update=True)

        fee_item.is_active = False
        fee_item.save(update_fields=['is_active'])

        return fee_item

    @classmethod
    @transaction.atomic
    def activate_fee_item(cls, user: User, fee_item_id: str) -> FeeItem:
        """
        Reactivate a previously deactivated fee item.

        :param user: User performing activation.
        :param fee_item_id: ID of the fee item.
        :return: Activated FeeItem instance.
        """
        fee_item = cls.get_fee_item(fee_item_id, is_active=False, select_for_update=True)

        fee_item.is_active = True
        fee_item.save(update_fields=['is_active'])

        return fee_item

    @classmethod
    def fetch_fee_item(cls, fee_item_id: str) -> dict:
        """
        Retrieve full fee item details including all grade-level fees.

        :param fee_item_id: ID of the fee item.
        :return: Dictionary with fee item and grade level fees.
        """
        fee_item = cls.get_fee_item(fee_item_id)

        grade_level_fees = list(
            GradeLevelFee.objects
            .filter(fee_item=fee_item)
            .values(
                'id', 'grade_level', 'term', 'academic_year',
                'amount', 'is_mandatory'
            )
        )

        branch_list = list(
            fee_item.branches.values('id', 'name') if fee_item.branches.exists() else []
        )

        return {
            'id': str(fee_item.id),
            'school_id': str(fee_item.school.id),
            'school_name': fee_item.school.name,
            'name': fee_item.name,
            'default_amount': fee_item.default_amount,
            'category': fee_item.category,
            'description': fee_item.description,
            'is_active': fee_item.is_active,
            'applies_to_all_branches': not fee_item.branches.exists(),
            'branches': branch_list,
            'created_at': fee_item.created_at,
            'updated_at': fee_item.updated_at,
            'grade_level_fees': grade_level_fees
        }

    @classmethod
    def list_fee_items(cls, user: User, **filters) -> List[dict]:
        """
        List all fee items with optional filtering.

        Available filters:
        - category
        - is_active (bool)
        - search_term (searches name and description)
        - grade_level, term, academic_year (returns only fee items that have a matching GradeLevelFee)

        :param user: User filtering.
        :param filters: Filter criteria.
        :return: List of fee item dictionaries with nested grade_level_fees.
        """
        field_types = {'is_active': bool}
        filters = cls._sanitize_and_validate_data(filters, field_types=field_types)

        qs = FeeItem.objects.filter(
            school=user.school,
            is_active=True,
            **filters
        ).select_related('school').prefetch_related('branches')

        if filters.get('is_active') is not None:
            qs = qs.filter(is_active=filters['is_active'])

        if filters.get('category'):
            qs = qs.filter(category=filters['category'])

        # Special handling for grade-level specific filters
        if any(k in filters for k in ['grade_level', 'term', 'academic_year']):
            glf_filters = Q()
            if filters.get('grade_level'):
                glf_filters &= Q(gradelevelfee__grade_level=filters['grade_level'])
            if filters.get('term'):
                glf_filters &= Q(gradelevelfee__term=filters['term'])
            if filters.get('academic_year'):
                glf_filters &= Q(gradelevelfee__academic_year=filters['academic_year'])
            qs = qs.filter(glf_filters).distinct()

        search_term = filters.get('search_term')
        if search_term:
            qs = qs.filter(
                Q(name__icontains=search_term) |
                Q(description__icontains=search_term)
            )

        qs = qs.order_by('category', 'name')

        return [cls.fetch_fee_item(str(fee_item.id)) for fee_item in qs]

    @classmethod
    @transaction.atomic
    def create_grade_level_fee(
        cls,
        user: User,
        fee_item_id: str,
        **data
    ) -> GradeLevelFee:
        """
        Create a grade-level specific fee override.

        :param user: User creating the record.
        :param fee_item_id: ID of the parent FeeItem.
        :param data: Must include grade_level, term, academic_year, amount.
        :return: Created GradeLevelFee instance.
        """
        required_fields = {'grade_level', 'term', 'academic_year', 'amount'}
        field_types = {'amount': float, 'is_mandatory': bool}

        data = cls._sanitize_and_validate_data(
            data,
            required_fields=required_fields,
            field_types=field_types
        )

        # Validate choices
        if data['grade_level'] not in dict(GradeLevel.choices):
            raise ValidationError(f"Invalid grade level: {data['grade_level']}")
        if data['term'] not in dict(Term.choices):
            raise ValidationError(f"Invalid term: {data['term']}")

        fee_item = cls.get_fee_item(fee_item_id)

        grade_level_fee = GradeLevelFee.objects.create(
            fee_item=fee_item,
            grade_level=data['grade_level'],
            term=data['term'],
            academic_year=data['academic_year'],
            amount=Decimal(str(data['amount'])),
            is_mandatory=data.get('is_mandatory', True)
        )

        return grade_level_fee

    @classmethod
    @transaction.atomic
    def update_grade_level_fee(
        cls,
        user: User,
        grade_level_fee_id: str,
        **data
    ) -> GradeLevelFee:
        """
        Update a grade-level fee.

        :param user: User performing update.
        :param grade_level_fee_id: ID of the GradeLevelFee.
        :param data: Fields to update.
        :return: Updated instance.
        """
        field_types = {'amount': float, 'is_mandatory': bool}
        data = cls._sanitize_and_validate_data(data, field_types=field_types)

        glf = GradeLevelFee.objects.select_for_update().get(id=grade_level_fee_id)

        update_fields = []

        if 'amount' in data:
            glf.amount = Decimal(str(data['amount']))
            update_fields.append('amount')

        if 'is_mandatory' in data:
            glf.is_mandatory = data['is_mandatory']
            update_fields.append('is_mandatory')

        if 'grade_level' in data:
            if data['grade_level'] not in dict(GradeLevel.choices):
                raise ValidationError(f"Invalid grade level: {data['grade_level']}")
            glf.grade_level = data['grade_level']
            update_fields.append('grade_level')

        if 'term' in data:
            if data['term'] not in dict(Term.choices):
                raise ValidationError(f"Invalid term: {data['term']}")
            glf.term = data['term']
            update_fields.append('term')

        if 'academic_year' in data:
            glf.academic_year = data['academic_year']
            update_fields.append('academic_year')

        if update_fields:
            glf.save(update_fields=update_fields)

        return glf

    @classmethod
    @transaction.atomic
    def delete_grade_level_fee(cls, user: User, grade_level_fee_id: str) -> None:
        """
        Hard delete a grade-level fee
        Here we do hard delete since it's configuration data.
        """
        GradeLevelFee.objects.get(id=grade_level_fee_id).delete()