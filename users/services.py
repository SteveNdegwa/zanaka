from users.models import AdminProfile, ClerkProfile, StudentProfile, GuardianProfile, StudentGuardian, User, Role, \
    RolePermission, Permission, ExtendedPermission, Device
from utils.service_base import ServiceBase



class RoleService(ServiceBase[Role]):
    manager = Role.objects


class PermissionService(ServiceBase[Permission]):
    manager = Permission.objects


class RolePermissionService(ServiceBase[RolePermission]):
    manager = RolePermission.objects


class ExtendedPermissionService(ServiceBase[ExtendedPermission]):
    manager = ExtendedPermission.objects


class UserService(ServiceBase[User]):
    manager = User.objects


class StudentGuardianService(ServiceBase[StudentGuardian]):
    manager = StudentGuardian.objects


class StudentProfileService(ServiceBase[StudentProfile]):
    manager = StudentProfile.objects


class GuardianProfileService(ServiceBase[GuardianProfile]):
    manager = GuardianProfile.objects


class ClerkProfileService(ServiceBase[ClerkProfile]):
    manager = ClerkProfile.objects


class AdminProfileService(ServiceBase[AdminProfile]):
    manager = AdminProfile.objects

class DeviceService(ServiceBase[Device]):
    manager = Device.objects
