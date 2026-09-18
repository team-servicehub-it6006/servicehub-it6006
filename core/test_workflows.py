from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group
from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from bookings.forms import AssignCleanerForm
from bookings.models import Booking, Status
from services.models import Service
from services.views import ServiceForm


class WorkflowRegressionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = cls.user('customer@example.com', 'Customer')
        cls.cleaner = cls.user('cleaner@example.com', 'Cleaner')
        cls.admin = cls.user('office@example.com', 'Administrator')
        cls.service = Service.objects.create(
            name='Standard clean', description='Regular clean', inclusions='Floors',
            base_price=Decimal('89'), duration_minutes=120)

    @staticmethod
    def user(email, role):
        user = User.objects.create_user(
            email, 'A-clean-home-2026!', first_name='Test', last_name=role,
            phone='021 555 0100')
        user.groups.add(Group.objects.get(name=role))
        return user

    def booking(self, status=Status.PENDING):
        return Booking.objects.create(
            customer=self.customer, cleaner=self.cleaner, service=self.service,
            scheduled_date=timezone.localdate() + timedelta(days=5),
            scheduled_time='09:00', street_address='12 Example Road', suburb='Mt Eden',
            postcode='1024', bedrooms=2, bathrooms=1, total_price=89,
            status=status, access_notes='Lockbox code 1234')

    def test_finished_jobs_cannot_be_reassigned(self):
        for status in [Status.COMPLETED, Status.CANCELLED, Status.IN_PROGRESS]:
            booking = self.booking(status)
            form = AssignCleanerForm({'cleaner': self.cleaner.pk}, booking=booking)
            self.assertFalse(form.is_valid())

    def test_assignment_post_leaves_finished_job_unchanged(self):
        booking = self.booking(Status.COMPLETED)
        self.client.force_login(self.admin)
        response = self.client.post(reverse('manage:assign', args=[booking.pk]),
                                    {'cleaner': self.cleaner.pk})
        self.assertContains(response, 'Only pending or confirmed')
        self.assertFalse(booking.history.exists())

    def test_slug_collision_does_not_crash_service_creation(self):
        other = Service.objects.create(
            name='Standard-clean', description='Another clean', inclusions='Floors',
            base_price=89, duration_minutes=120)
        self.assertNotEqual(self.service.slug, other.slug)
        self.assertTrue(other.slug)

    def test_duration_changes_cannot_overlap_existing_assignments(self):
        self.booking(Status.CONFIRMED)
        form = ServiceForm({
            'name': self.service.name, 'description': 'Regular clean',
            'inclusions': 'Floors', 'base_price': '89', 'duration_minutes': '240',
            'is_active': 'on'}, instance=self.service)
        self.assertFalse(form.is_valid())
        self.assertIn('duration_minutes', form.errors)

    def test_cleanup_uses_recorded_finish_date_not_scheduled_date(self):
        booking = self.booking(Status.IN_PROGRESS)
        booking.scheduled_date = timezone.localdate() - timedelta(days=60)
        booking.save()
        booking.record_status(Status.COMPLETED, self.cleaner)
        call_command('clear_access_notes')
        booking.refresh_from_db()
        self.assertTrue(booking.access_notes)
        booking.history.update(changed_at=timezone.now() - timedelta(days=31))
        call_command('clear_access_notes', dry_run=True)
        booking.refresh_from_db()
        self.assertTrue(booking.access_notes)
        call_command('clear_access_notes')
        booking.refresh_from_db()
        self.assertEqual(booking.access_notes, '')

    def test_cleanup_does_not_clear_active_bookings(self):
        booking = self.booking(Status.CONFIRMED)
        booking.history.create(from_status='pending', to_status='confirmed',
                               changed_by=self.admin)
        booking.history.update(changed_at=timezone.now() - timedelta(days=90))
        call_command('clear_access_notes')
        booking.refresh_from_db()
        self.assertTrue(booking.access_notes)

    def test_customer_pagination_can_reach_second_page(self):
        for _ in range(21):
            self.booking()
        self.client.force_login(self.customer)
        response = self.client.get(reverse('bookings:mine'))
        self.assertContains(response, 'Page 1 of 2')
        response = self.client.get(reverse('bookings:mine') + '?page=2')
        self.assertEqual(len(response.context['bookings']), 1)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_password_reset_completes_with_a_real_token(self):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        response = self.client.post(reverse('accounts:password_reset'),
                                    {'email': self.customer.email})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        uid = urlsafe_base64_encode(force_bytes(self.customer.pk))
        token = default_token_generator.make_token(self.customer)
        response = self.client.get(reverse('accounts:password_reset_confirm',
                                           args=[uid, token]))
        response = self.client.post(response.url, {
            'new_password1': 'A-new-clean-home-2026!',
            'new_password2': 'A-new-clean-home-2026!'})
        self.assertRedirects(response, reverse('accounts:password_reset_complete'))
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.check_password('A-new-clean-home-2026!'))

    def test_password_change_preserves_session(self):
        self.client.force_login(self.customer)
        response = self.client.post(reverse('accounts:password_change'), {
            'old_password': 'A-clean-home-2026!',
            'new_password1': 'A-new-clean-home-2026!',
            'new_password2': 'A-new-clean-home-2026!'})
        self.assertRedirects(response, reverse('accounts:password_change_done'))
        self.assertEqual(self.client.get(reverse('accounts:profile')).status_code, 200)

    def test_administrator_can_edit_and_cancel_customer_booking(self):
        booking = self.booking()
        self.client.force_login(self.admin)
        response = self.client.post(reverse('bookings:edit', args=[booking.pk]), {
            'scheduled_date': booking.scheduled_date.isoformat(),
            'scheduled_time': '13:00', 'street_address': '24 Example Road',
            'suburb': 'Mt Eden', 'postcode': '1024', 'bedrooms': 3, 'bathrooms': 1,
            'access_notes': 'Side entrance'})
        self.assertEqual(response.status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.street_address, '24 Example Road')
        self.assertEqual(booking.total_price, Decimal('114'))
        self.assertEqual(booking.customer, self.customer)
        response = self.client.post(reverse('bookings:cancel', args=[booking.pk]),
                                    {'note': 'Customer requested cancellation'})
        self.assertRedirects(response, reverse('manage:bookings'))
        booking.refresh_from_db()
        self.assertEqual(booking.status, Status.CANCELLED)
        from core.models import AuditLog
        self.assertTrue(AuditLog.objects.filter(action='booking_updated').exists())
        self.assertTrue(AuditLog.objects.filter(action='booking_cancelled').exists())

    def test_cleaner_cannot_edit_or_cancel_customer_booking(self):
        booking = self.booking()
        self.client.force_login(self.cleaner)
        for name in ['bookings:edit', 'bookings:cancel']:
            self.assertEqual(self.client.post(reverse(name, args=[booking.pk]), {}).status_code, 403)

    @override_settings(DEBUG=False)
    def test_demo_seed_is_blocked_in_production(self):
        count = User.objects.count()
        with self.assertRaises(CommandError):
            call_command('seed_demo')
        self.assertEqual(User.objects.count(), count)
