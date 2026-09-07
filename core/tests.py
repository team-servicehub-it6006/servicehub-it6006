"""
Checks on the data layer.

These are not the access-control tests, which drive real URLs and come later. These only pin
down the rules that live in the models: the price the server works out, the status moves the
business allows, and who a booking belongs to. All three are places where trusting the browser
would be a security bug, so they get a test from the day they are written.
"""
from datetime import date, time
from decimal import Decimal

from django.contrib.auth.models import Group
from django.test import TestCase

from accounts.models import ADMINISTRATOR, CLEANER, CUSTOMER, User
from bookings.models import Booking, Status
from services.models import Service


class UserModelTests(TestCase):

    def test_email_is_stored_lower_case(self):
        # Otherwise Himani@example.com and himani@example.com become two accounts and the
        # unique constraint never notices.
        user = User.objects.create_user('Himani@Example.COM', 'a-long-enough-password')
        self.assertEqual(user.email, 'himani@example.com')

    def test_a_new_user_holds_no_role(self):
        user = User.objects.create_user('nobody@example.com', 'a-long-enough-password')
        self.assertEqual(user.role_names, [])
        self.assertFalse(user.is_customer)
        self.assertFalse(user.is_cleaner)
        self.assertFalse(user.is_administrator)

    def test_role_comes_from_group_membership(self):
        user = User.objects.create_user('cleaner@example.com', 'a-long-enough-password')
        user.groups.add(Group.objects.get(name=CLEANER))
        self.assertTrue(user.is_cleaner)
        self.assertFalse(user.is_customer)


class RoleTests(TestCase):

    def test_the_three_roles_exist_after_migrating(self):
        self.assertEqual(Group.objects.filter(
            name__in=[CUSTOMER, CLEANER, ADMINISTRATOR]).count(), 3)

    def test_a_cleaner_cannot_see_every_booking(self):
        # The permission that separates an administrator from everyone else.
        cleaner = Group.objects.get(name=CLEANER)
        admin = Group.objects.get(name=ADMINISTRATOR)
        self.assertFalse(cleaner.permissions.filter(codename='view_all_bookings').exists())
        self.assertTrue(admin.permissions.filter(codename='view_all_bookings').exists())


class ServicePricingTests(TestCase):

    def setUp(self):
        self.service = Service.objects.create(
            name='Deep clean', description='x', inclusions='Kitchen\nBathroom',
            base_price=Decimal('180.00'), duration_minutes=180)

    def test_standard_property_pays_the_base_price(self):
        self.assertEqual(self.service.price_for(2, 1), Decimal('180.00'))

    def test_a_smaller_property_is_not_charged_less_than_the_base(self):
        self.assertEqual(self.service.price_for(1, 1), Decimal('180.00'))

    def test_extra_rooms_add_to_the_price(self):
        # 180 + two extra bedrooms at 25 + one extra bathroom at 30
        self.assertEqual(self.service.price_for(4, 2), Decimal('260.00'))

    def test_slug_is_filled_in_on_save(self):
        self.assertEqual(self.service.slug, 'deep-clean')


class BookingTests(TestCase):

    def setUp(self):
        self.customer = User.objects.create_user('c@example.com', 'a-long-enough-password')
        self.cleaner = User.objects.create_user('cl@example.com', 'a-long-enough-password')
        self.other = User.objects.create_user('nosy@example.com', 'a-long-enough-password')
        self.service = Service.objects.create(
            name='Standard clean', description='x', inclusions='Kitchen',
            base_price=Decimal('120.00'), duration_minutes=120)
        self.booking = Booking.objects.create(
            customer=self.customer, cleaner=self.cleaner, service=self.service,
            scheduled_date=date(2026, 10, 1), scheduled_time=time(9, 0),
            street_address='12 Queen St', suburb='Newtown', postcode='6021',
            bedrooms=2, bathrooms=1, total_price=self.service.price_for(2, 1))

    def test_reference_is_generated_and_unique(self):
        second = Booking.objects.create(
            customer=self.customer, service=self.service,
            scheduled_date=date(2026, 10, 2), scheduled_time=time(9, 0),
            street_address='14 Queen St', suburb='Newtown', postcode='6021',
            bedrooms=2, bathrooms=1, total_price=Decimal('120.00'))
        self.assertTrue(self.booking.reference.startswith('SH-'))
        self.assertNotEqual(self.booking.reference, second.reference)

    def test_the_customer_and_the_assigned_cleaner_can_see_it(self):
        self.assertTrue(self.booking.visible_to(self.customer))
        self.assertTrue(self.booking.visible_to(self.cleaner))

    def test_an_unrelated_signed_in_user_cannot(self):
        # This is the object-level rule. Holding the Customer role is not enough; the booking
        # has to actually be yours.
        self.other.groups.add(Group.objects.get(name=CUSTOMER))
        self.assertFalse(self.booking.visible_to(self.other))

    def test_a_cancelled_booking_cannot_be_confirmed_again(self):
        self.booking.record_status(Status.CANCELLED, self.customer)
        self.assertFalse(self.booking.can_transition_to(Status.CONFIRMED))
        self.assertFalse(self.booking.is_editable)

    def test_the_allowed_move_is_permitted_and_written_down(self):
        self.assertTrue(self.booking.can_transition_to(Status.CONFIRMED))
        self.booking.record_status(Status.CONFIRMED, self.customer, note='paid')
        entry = self.booking.history.get()
        self.assertEqual((entry.from_status, entry.to_status),
                         (Status.PENDING, Status.CONFIRMED))
        self.assertEqual(entry.changed_by, self.customer)
