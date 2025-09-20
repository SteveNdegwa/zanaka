from audit.decorators import set_activity_name
from authentication.decorators import user_login_required
from base.views import BaseView
from users.services.user_service import UserService
from utils.response_provider import ResponseProvider


class StudentGuardianView(BaseView):
    @user_login_required
    @set_activity_name('Assign guardian to student')
    def post(self, request, student_id, guardian_id, *args, **kwargs):
        relationship = self.data.get('relationship')
        is_primary = self.data.get('is_primary', False)
        can_receive_reports = self.data.get('can_receive_reports', False)

        UserService.add_guardian_to_student(
            student_id=student_id,
            guardian_id=guardian_id,
            relationship=relationship,
            is_primary=is_primary,
            can_receive_reports=can_receive_reports
        )

        return ResponseProvider.created()

    @user_login_required
    @set_activity_name('Remove guardian from student')
    def delete(self, request, student_id, guardian_id, *args, **kwargs):
        UserService.remove_guardian_from_student(
            student_id=student_id,
            guardian_id=guardian_id
        )

        return ResponseProvider.success()
