import uuid
from datetime import datetime, timedelta

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string


class Status(models.TextChoices):
    PENDING = 'pending', 'Pending'
    CONFIRMED = 'confirmed', 'Confirmed'
    IN_PROGRESS = 'in_progress', 'In progress'
    COMPLETED = 'completed', 'Completed'
    CANCELLED = 'cancelled', 'Cancelled'


# The only transitions the business allows. Declared once, checked on the server, so a
# hand-crafted POST cannot move a cancelled booking back to confirmed.
ALLOWED_TRANSITIONS = {
    Status.PENDING: {Status.CONFIRMED, Status.CANCELLED},
    Status.CONFIRMED: {Status.IN_PROGRESS, Status.CANCELLED},
    Status.IN_PROGRESS: {Status.COMPLETED},
    Status.COMPLETED: set(),
    Status.CANCELLED: set(),
}

EDITABLE_STATUSES = {Status.PENDING, Status.CONFIRMED}

STATUS_BADGE = {
    Status.PENDING: 'warning',
    Status.CONFIRMED: 'primary',
    Status.IN_PROGRESS: 'info',
    Status.COMPLETED: 'success',
    Status.CANCELLED: 'secondary',
}


class BookingQuerySet(models.QuerySet):
    def for_customer(self, user):
        return self.filter(customer=user)

    def for_cleaner(self, user):
        return self.filter(cleaner=user)

    def upcoming(self):
        return self.filter(scheduled_date__gte=timezone.localdate())


class Booking(models.Model):
    """One job, at one address, on one date. The central record in the system."""

    # A UUID rather than an auto integer, specifically so that booking URLs cannot be walked
    # by counting. The object-level permission check is the real control; this is the layer
    # underneath it.
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=10, unique=True, editable=False)

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                 related_name='bookings')
    cleaner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                null=True, blank=True, related_name='jobs')
    service = models.ForeignKey('services.Service', on_delete=models.PROTECT,
                                related_name='bookings')

    scheduled_date = models.DateField()
    scheduled_time = models.TimeField()

    street_address = models.CharField(max_length=120)
    suburb = models.CharField(max_length=80)
    postcode = models.CharField(max_length=8)
    bedrooms = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)])
    bathrooms = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(6)])
    access_notes = models.TextField(
        blank=True,
        help_text='Optional. How the cleaner gets in. Cleared 30 days after the job is done.')

    total_price = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = BookingQuerySet.as_manager()

    class Meta:
        ordering = ['-scheduled_date', '-scheduled_time']
        indexes = [
            models.Index(fields=['customer', '-scheduled_date']),
            models.Index(fields=['cleaner', 'scheduled_date']),
            models.Index(fields=['status']),
        ]
        permissions = [
            ('view_all_bookings', 'Can view every booking'),
            ('assign_cleaner', 'Can assign a cleaner to a booking'),
            ('update_job_status', 'Can move an assigned job through its statuses'),
        ]

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self._new_reference()
        return super().save(*args, **kwargs)

    @staticmethod
    def _new_reference():
        for _ in range(20):
            candidate = 'SH-' + get_random_string(4, '0123456789ABCDEF')
            if not Booking.objects.filter(reference=candidate).exists():
                return candidate
        raise RuntimeError('Could not generate a unique booking reference.')

    def __str__(self):
        return f'{self.reference} {self.service} on {self.scheduled_date}'

    def get_absolute_url(self):
        return reverse('bookings:detail', args=[self.id])

    # --- helpers used by the views and templates ---------------------------------
    @property
    def badge(self):
        return STATUS_BADGE.get(self.status, 'secondary')

    @property
    def is_editable(self):
        return self.status in EDITABLE_STATUSES

    @property
    def address(self):
        return f'{self.street_address}, {self.suburb} {self.postcode}'.strip()

    @property
    def starts_at(self):
        return timezone.make_aware(
            datetime.combine(self.scheduled_date, self.scheduled_time),
            timezone.get_current_timezone())

    @property
    def ends_at(self):
        return self.starts_at + timedelta(minutes=self.service.duration_minutes)

    def can_transition_to(self, new_status):
        return new_status in ALLOWED_TRANSITIONS.get(self.status, set())

    def visible_to(self, user):
        """The single place that answers 'is this booking any of your business?'."""
        if not user.is_authenticated:
            return False
        return (self.customer_id == user.id
                or self.cleaner_id == user.id
                or user.has_perm('bookings.view_all_bookings'))

    def record_status(self, new_status, changed_by, note=''):
        old = self.status
        self.status = new_status
        self.save(update_fields=['status', 'updated_at'])
        BookingStatusHistory.objects.create(
            booking=self, from_status=old, to_status=new_status,
            changed_by=changed_by, note=note)


class BookingStatusHistory(models.Model):
    """One row per status change. This is what settles an argument about a past job."""

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='history')
    from_status = models.CharField(max_length=12, choices=Status.choices)
    to_status = models.CharField(max_length=12, choices=Status.choices)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['changed_at']
        verbose_name_plural = 'booking status history'

    def __str__(self):
        return f'{self.booking.reference}: {self.from_status} to {self.to_status}'
