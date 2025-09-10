from school.models import School, Branch, Classroom
from utils.service_base import ServiceBase


class SchoolService(ServiceBase[School]):
    manager = School.objects


class BranchService(ServiceBase[Branch]):
    manager = Branch.objects


class ClassroomService(ServiceBase[Classroom]):
    manager = Classroom.objects
