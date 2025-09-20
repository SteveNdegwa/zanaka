from django.core.management.base import BaseCommand

from base.db_manager import DBManager


class Command(BaseCommand):
    help = "Reintegrate the old primary as replica and sync data"

    def handle(self, *args, **options):
        DBManager.reintegrate_old_primary()
        self.stdout.write(self.style.SUCCESS("Old primary reintegrated as replica"))
