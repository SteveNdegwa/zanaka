from datetime import timedelta

from django.core.management import BaseCommand
from django.utils import timezone

from audit.services import AuditLogService


class Command(BaseCommand):
    help = 'Clean up old audit logs based on retention policies'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=None,
            help='Days to retain (overrides model configuration)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        retention_days = options['days'] or 2555  # Default 7 years
        cutoff_date = timezone.now() - timedelta(days=retention_days)

        old_logs = AuditLogService().filter(date_created__lt=cutoff_date)
        count = old_logs.count()

        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(f'Would delete {count} audit log entries older than {retention_days} days')
            )
        else:
            deleted_count, _ = old_logs.delete()
            self.stdout.write(
                self.style.SUCCESS(f'Deleted {deleted_count} audit log entries older than {retention_days} days')
            )
