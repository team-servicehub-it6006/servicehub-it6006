"""
Access control tests.

These exist because a missing permission mixin is invisible. The code looks fine, the page
loads, and the hole is only found by someone who goes looking. Driving every role at every URL
and asserting the answer means a decorator cannot be dropped without the build going red.
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from services.models import Service

from .models import Booking, Status

User = get_user_model()
PASSWORD = 'a-long-enough-test-password'


def make_user(email, role, **extra):
    user = User.objects.create_user(
        email=email, password=PASSWORD,
        first_name=extra.pop('first_name', 'Test'),
        last_name=extra.pop('last_name', 'User'),
        phone=extra.pop('phone', '021 555 0000'), **extra)
    user.groups.add(Group.objects.get(name=role))
    return user


class BaseFixture(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.service = Service.objects.create(
            name='Deep clean', description='d', inclusions='a\nb',
            base_price=Decimal('180.00'), duration_minutes=270)
        cls.owner = make_user('owner@example.com', 'Customer', first_name='Owner')
        cls.other = make_user('other@example.com', 'Customer', first_name='Other')
        cls.cleaner = make_user('cleaner@example.com', 'Cleaner', first_name='Aroha')
        cls.other_cleaner = make_user('cleaner2@example.com', 'Cleaner', first_name='Sione')
        cls.admin = make_user('admin@example.com', 'Administrator', first_name='Priya')

        cls.booking = Booking.objects.create(
            customer=cls.owner, cleaner=cls.cleaner, service=cls.service,
            scheduled_date=timezone.localdate() + timedelta(days=3),
            scheduled_time='09:00', street_address='12 Example Road', suburb='Mt Eden',
            postcode='1024', bedrooms=3, bathrooms=2,
            total_price=Decimal('235.00'), status=Status.CONFIRMED)


class BookingAccessTests(BaseFixture):
    """Who may open one particular booking."""

    def url(self):
        return reverse('bookings:detail', args=[self.booking.pk])

    def test_anonymous_is_sent_to_the_sign_in_page(self):
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_owner_can_open_their_own_booking(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.url()).status_code, 200)

    def test_another_customer_is_refused(self):
        # The important one. Guessing a UUID is impractical, but if one leaks the record still
        # must not open.
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url()).status_code, 403)

    def test_assigned_cleaner_can_open_it(self):
        self.client.force_login(self.cleaner)
        self.assertEqual(self.client.get(self.url()).status_code, 200)

    def test_unassigned_cleaner_is_refused(self):
        # Holding the Cleaner role is not enough. Every cleaner has the same permission, so the
        # object check is what keeps them apart.
        self.client.force_login(self.other_cleaner)
        self.assertEqual(self.client.get(self.url()).status_code, 403)

    def test_administrator_can_open_any_booking(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.url()).status_code, 200)


class ListScopeTests(BaseFixture):
    """A list must not leak a record the reader may not open."""

    def test_customer_list_contains_only_their_own(self):
        Booking.objects.create(
            customer=self.other, service=self.service,
            scheduled_date=timezone.localdate() + timedelta(days=4), scheduled_time='10:00',
            street_address='8 Sample Street', suburb='Onehunga', postcode='1061',
            bedrooms=2, bathrooms=1, total_price=Decimal('180.00'))
        self.client.force_login(self.owner)
        bookings = self.client.get(reverse('bookings:mine')).context['bookings']
        self.assertEqual([b.pk for b in bookings], [self.booking.pk])

    def test_cleaner_job_list_contains_only_their_jobs(self):
        self.client.force_login(self.other_cleaner)
        jobs = self.client.get(reverse('staff:jobs')).context['jobs']
        self.assertEqual(list(jobs), [])

    def test_customer_cannot_reach_the_cleaner_job_list(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse('staff:jobs')).status_code, 403)


class ManagementUrlTests(BaseFixture):
    """Everything under /manage/ is administrator-only."""

    MANAGE_URLS = ['manage:bookings', 'manage:services', 'manage:users', 'manage:audit']

    def test_customer_is_refused_every_management_url(self):
        self.client.force_login(self.owner)
        for name in self.MANAGE_URLS:
            with self.subTest(url=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)

    def test_cleaner_is_refused_every_management_url(self):
        self.client.force_login(self.cleaner)
        for name in self.MANAGE_URLS:
            with self.subTest(url=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)

    def test_administrator_reaches_every_management_url(self):
        self.client.force_login(self.admin)
        for name in self.MANAGE_URLS:
            with self.subTest(url=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)


class StatusTransitionTests(BaseFixture):
    """The status machine is enforced on the server, not by which buttons are drawn."""

    def post_status(self, status):
        return self.client.post(reverse('staff:job_status', args=[self.booking.pk]),
                                {'status': status})

    def test_assigned_cleaner_can_start_a_confirmed_job(self):
        self.client.force_login(self.cleaner)
        self.post_status(Status.IN_PROGRESS)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Status.IN_PROGRESS)

    def test_illegal_transition_is_rejected(self):
        # Confirmed straight to completed is not a move the business allows, and the buttons
        # never offer it. This posts it by hand anyway.
        self.client.force_login(self.cleaner)
        self.post_status(Status.COMPLETED)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Status.CONFIRMED)

    def test_cleaner_cannot_touch_a_job_that_is_not_theirs(self):
        self.client.force_login(self.other_cleaner)
        self.assertEqual(self.post_status(Status.IN_PROGRESS).status_code, 403)

    def test_a_cancelled_booking_cannot_be_revived(self):
        self.booking.record_status(Status.CANCELLED, self.owner)
        self.client.force_login(self.admin)
        self.post_status(Status.CONFIRMED)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Status.CANCELLED)


class PriceIntegrityTests(BaseFixture):
    """The price is worked out on the server and never read from the form."""

    def test_price_comes_from_the_service_not_the_request(self):
        self.client.force_login(self.owner)
        self.client.post(
            reverse('bookings:create', args=[self.service.slug]),
            {'scheduled_date': (timezone.localdate() + timedelta(days=5)).isoformat(),
             'scheduled_time': '09:00', 'street_address': '12 Example Road',
             'suburb': 'Mt Eden', 'postcode': '1024', 'bedrooms': 3, 'bathrooms': 2,
             'access_notes': '', 'total_price': '1.00'})
        created = Booking.objects.filter(customer=self.owner).order_by('-created_at').first()
        self.assertEqual(created.total_price, Decimal('235.00'))
