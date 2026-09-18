from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Max
from django.utils import timezone

from bookings.models import Booking, Status


class Command(BaseCommand):
    help = 'Clear access notes 30 days after the latest completion or cancellation.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=30)
        bookings = Booking.objects.filter(
            status__in=[Status.COMPLETED, Status.CANCELLED]
        ).exclude(access_notes='').annotate(
            finished_at=Max('history__changed_at')
        ).filter(finished_at__lte=cutoff)
        ids = list(bookings.values_list('pk', flat=True))
        if not options['dry_run']:
            Booking.objects.filter(pk__in=ids).update(access_notes='')
        action = 'Would clear' if options['dry_run'] else 'Cleared'
        self.stdout.write(f'{action} access notes for {len(ids)} bookings.')
