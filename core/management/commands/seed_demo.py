"""
Demo data for a fresh database.

Running the app on an empty database shows empty tables on every screen, which makes it
impossible to tell a working page from a broken one. This fills in the catalogue, one account
per role and a booking in every status, so each screen has something on it.

Safe to run more than once: everything is matched on a natural key and updated rather than
duplicated.
"""
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import ADMINISTRATOR, CLEANER, CUSTOMER, User
from bookings.models import Booking, Status
from services.models import Service

PASSWORD = 'ServiceHub2026!'

SERVICES = [
    {
        'name': 'Standard clean',
        'description': 'Kitchen, bathroom, floors and a general tidy. Best for a regular '
                       'fortnightly booking.',
        'inclusions': 'Kitchen benches and sink\nBathroom and toilet\nVacuum and mop\n'
                      'Dusting and general tidy\nRubbish out',
        'base_price': Decimal('89.00'),
        'duration_minutes': 120,
        'is_active': True,
    },
    {
        'name': 'Deep clean',
        'description': 'Everything in a standard clean plus oven, windows, skirting and inside '
                       'cupboards.',
        'inclusions': 'Everything in a standard clean\nOven and rangehood\nInside cupboards\n'
                      'Windows and tracks\nSkirting boards',
        'base_price': Decimal('180.00'),
        'duration_minutes': 270,
        'is_active': True,
    },
    {
        'name': 'End of tenancy',
        'description': 'Bond-return clean, done to the checklist most property managers use.',
        'inclusions': 'Full deep clean\nInside wardrobes and drawers\nWalls spot cleaned\n'
                      'Carpets vacuumed and edges done\nGarage swept',
        'base_price': Decimal('260.00'),
        'duration_minutes': 360,
        'is_active': True,
    },
    {
        'name': 'Office clean',
        'description': 'After hours clean for small offices. Currently not taking new bookings.',
        'inclusions': 'Desks and surfaces\nKitchenette\nBathrooms\nVacuum and mop\n'
                      'Rubbish and recycling',
        'base_price': Decimal('140.00'),
        'duration_minutes': 180,
        'is_active': False,
    },
]

PEOPLE = [
    # email, first name, last name, phone, suburb, role
    ('h.thapa@example.com', 'Himani', 'Thapa Magar', '021 555 0101', 'Mt Eden', CUSTOMER),
    ('j.singh@example.com', 'Jyoti', 'Singh', '021 555 0102', 'Onehunga', CUSTOMER),
    ('a.williams@example.com', 'Aroha', 'Williams', '021 555 0201', 'Ellerslie', CLEANER),
    ('s.pousini@example.com', 'Sione', 'Pousini', '021 555 0202', 'Papatoetoe', CLEANER),
    ('p.raman@example.com', 'Priya', 'Raman', '09 555 1234', 'Newmarket', ADMINISTRATOR),
]

ADDRESSES = [
    ('12 Example Road', 'Mt Eden', '1024', 3, 2),
    ('8 Sample Street', 'Onehunga', '1061', 2, 1),
    ('44 Test Avenue', 'Ellerslie', '1051', 4, 2),
    ('2 Demo Crescent', 'Papatoetoe', '2025', 2, 1),
]

# The route each booking takes to reach its final status. Walking the real transitions rather
# than writing the status straight in means the history table and the status rules are exercised
# by the seed, so a broken transition shows up here rather than in front of a marker.
ROUTES = {
    Status.PENDING: [],
    Status.CONFIRMED: [Status.CONFIRMED],
    Status.IN_PROGRESS: [Status.CONFIRMED, Status.IN_PROGRESS],
    Status.COMPLETED: [Status.CONFIRMED, Status.IN_PROGRESS, Status.COMPLETED],
    Status.CANCELLED: [Status.CANCELLED],
}


class Command(BaseCommand):
    help = 'Fill an empty database with the services, accounts and bookings used for the demo.'

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('Demo accounts can only be created with DEBUG enabled.')
        services = {row['name']: self._service(row) for row in SERVICES}
        people = {row[0]: self._person(*row) for row in PEOPLE}
        admin = self._superuser()
        self._bookings(services, people, admin)

        self.stdout.write(self.style.SUCCESS(
            '{} services, {} users and {} bookings are in the database.'.format(
                Service.objects.count(), User.objects.count(), Booking.objects.count())))
        self.stdout.write('Every demo account uses the password ' + PASSWORD)
        self.stdout.write('Administrator p.raman@example.com, '
                          'cleaner a.williams@example.com, customer h.thapa@example.com')

    def _service(self, row):
        service, _ = Service.objects.update_or_create(name=row['name'], defaults=row)
        return service

    def _person(self, email, first_name, last_name, phone, suburb, role):
        person = User.objects.filter(email=email).first()
        if person is None:
            person = User.objects.create_user(email, PASSWORD, first_name=first_name,
                                              last_name=last_name, phone=phone, suburb=suburb)
        person.groups.set([Group.objects.get(name=role)])
        return person

    def _superuser(self):
        email = 'admin@servicehub.local'
        admin = User.objects.filter(email=email).first()
        if admin is None:
            admin = User.objects.create_superuser(
                email, PASSWORD, first_name='Office', last_name='Admin', phone='09 555 0000')
        return admin

    def _bookings(self, services, people, admin):
        if Booking.objects.exists():
            self.stdout.write('Bookings already exist, leaving them alone.')
            return

        today = timezone.localdate()
        himani = people['h.thapa@example.com']
        jyoti = people['j.singh@example.com']
        aroha = people['a.williams@example.com']
        sione = people['s.pousini@example.com']

        # customer, service, cleaner, days from today, start time, final status
        plan = [
            (himani, 'Deep clean', None, 7, '09:00', Status.PENDING),
            (himani, 'Standard clean', aroha, 1, '13:00', Status.CONFIRMED),
            (himani, 'Standard clean', aroha, -14, '13:00', Status.COMPLETED),
            (himani, 'End of tenancy', sione, -30, '08:00', Status.CANCELLED),
            (jyoti, 'Deep clean', aroha, 2, '09:00', Status.CONFIRMED),
            (jyoti, 'Standard clean', sione, 0, '10:00', Status.IN_PROGRESS),
        ]

        for index, row in enumerate(plan):
            customer, service_name, cleaner, offset, start_time, final_status = row
            service = services[service_name]
            street, suburb, postcode, bedrooms, bathrooms = ADDRESSES[index % len(ADDRESSES)]
            booking = Booking.objects.create(
                customer=customer,
                cleaner=cleaner,
                service=service,
                scheduled_date=today + timedelta(days=offset),
                scheduled_time=start_time,
                street_address=street,
                suburb=suburb,
                postcode=postcode,
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                access_notes='Key is in the lockbox by the front door.' if cleaner else '',
                total_price=service.price_for(bedrooms, bathrooms),
            )
            self._walk_to(booking, final_status, admin)

    def _walk_to(self, booking, final_status, admin):
        for step in ROUTES[final_status]:
            by_cleaner = step in {Status.IN_PROGRESS, Status.COMPLETED}
            actor = booking.cleaner if by_cleaner and booking.cleaner else admin
            booking.record_status(step, actor)
