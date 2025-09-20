from django.core.management.base import BaseCommand

from base.db_manager import DBManager


class Command(BaseCommand):
    help = "Promote replica to be the new primary"

    def handle(self, *args, **options):
        DBManager.promote_replica()
        self.stdout.write(self.style.SUCCESS("Replica promoted to primary"))
