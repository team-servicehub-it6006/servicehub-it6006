from datetime import time, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.models import ADMINISTRATOR, CLEANER, CUSTOMER
from bookings.models import Booking, Status
from services.models import Service

User = get_user_model()
PASSWORD = 'ServiceHub2026!'

SERVICES = [
    {
        'name': 'Standard clean',
        'description': 'A regular home clean for kitchens, bathrooms and living areas.',
        'inclusions': 'Kitchen surfaces\nBathroom surfaces\nVacuum and mop floors\nDust reachable surfaces',
        'base_price': Decimal('89.00'),
        'duration_minutes': 120,
        'is_active': True,
    },
    {
        'name': 'Deep clean',
        'description': 'A more detailed clean for homes that need extra attention.',
        'inclusions': 'Everything in a standard clean\nDetailed kitchen clean\nDetailed bathroom clean\nSkirting boards and doors',
        'base_price': Decimal('180.00'),
        'duration_minutes': 270,
        'is_active': True,
    },
    {
        'name': 'End of tenancy',
        'description': 'A full property clean for moving out or preparing for new tenants.',
        'inclusions': 'Kitchen and appliances\nBathrooms\nAll floors\nInside cupboards\nGeneral dusting',
        'base_price': Decimal('260.00'),
        'duration_minutes': 360,
        'is_active': True,
    },
    {
        'name': 'Office clean',
        'description': 'A small-office cleaning service kept for historical bookings.',
        'inclusions': 'Desks and common areas\nKitchenette\nBathrooms\nVacuum and mop floors',
        'base_price': Decimal('140.00'),
        'duration_minutes': 180,
        'is_active': False,
    },
]

PEOPLE = [
    ('h.thapa@example.com', 'Himani', 'Thapa Magar', '021 555 0101', 'Mt Eden', CUSTOMER),
    ('j.singh@example.com', 'Jyoti', 'Singh', '021 555 0102', 'Onehunga', CUSTOMER),
    ('a.williams@example.com', 'Aroha', 'Williams', '021 555 0201', 'Ellerslie', CLEANER),
    ('s.pousini@example.com', 'Sione', 'Pousini', '021 555 0202', 'Papatoetoe', CLEANER),
    ('p.raman@example.com', 'Priya', 'Raman', '09 555 1234', 'Newmarket', ADMINISTRATOR),
]

ROUTES = {
    Status.PENDING: [],
    Status.CONFIRMED: [Status.CONFIRMED],
    Status.IN_PROGRESS: [Status.CONFIRMED, Status.IN_PROGRESS],
    Status.COMPLETED: [Status.CONFIRMED, Status.IN_PROGRESS, Status.COMPLETED],
    Status.CANCELLED: [Status.CANCELLED],
}


class Command(BaseCommand):
    help = 'Create repeatable demo services, users and bookings for ServiceHub.'

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('seed_demo is disabled when DEBUG is off.')

        groups = {}
        for role in (CUSTOMER, CLEANER, ADMINISTRATOR):
            groups[role], _ = Group.objects.get_or_create(name=role)

        services = {}
        for row in SERVICES:
            service, _ = Service.objects.update_or_create(
                name=row['name'],
                defaults=row,
            )
            services[row['name']] = service

        users = {}
        for email, first_name, last_name, phone, suburb, role in PEOPLE:
            user = User.objects.filter(email=email).first()
            if user is None:
                user = User.objects.create_user(
                    email=email,
                    password=PASSWORD,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    suburb=suburb,
                )
            else:
                user.first_name = first_name
                user.last_name = last_name
                user.phone = phone
                user.suburb = suburb
                user.set_password(PASSWORD)
                user.save()
            user.groups.set([groups[role]])
            users[email] = user

        admin = User.objects.filter(email='admin@servicehub.local').first()
        if admin is None:
            admin = User.objects.create_superuser(
                email='admin@servicehub.local',
                password=PASSWORD,
                first_name='ServiceHub',
                last_name='Admin',
                phone='09 555 0100',
                suburb='Auckland',
            )
        else:
            admin.first_name = 'ServiceHub'
            admin.last_name = 'Admin'
            admin.phone = '09 555 0100'
            admin.suburb = 'Auckland'
            admin.is_staff = True
            admin.is_superuser = True
            admin.set_password(PASSWORD)
            admin.save()
            admin.groups.add(groups[ADMINISTRATOR])
        users[admin.email] = admin

        if not Booking.objects.exists():
            today = timezone.localdate()
            customer1 = users['h.thapa@example.com']
            customer2 = users['j.singh@example.com']
            cleaner1 = users['a.williams@example.com']
            cleaner2 = users['s.pousini@example.com']

            rows = [
                (customer1, None, 'Standard clean', 2, time(9, 0), '12 Queen Street', 'Auckland Central', '1010', 2, 1, Status.PENDING),
                (customer2, cleaner1, 'Deep clean', 3, time(10, 0), '8 Green Lane', 'Epsom', '1023', 3, 2, Status.CONFIRMED),
                (customer1, cleaner2, 'Standard clean', 4, time(13, 0), '22 Dominion Road', 'Mt Eden', '1024', 2, 1, Status.IN_PROGRESS),
                (customer2, cleaner1, 'End of tenancy', -3, time(8, 0), '15 Great South Road', 'Newmarket', '1023', 3, 2, Status.COMPLETED),
                (customer1, None, 'Standard clean', 6, time(14, 0), '31 Manukau Road', 'Epsom', '1023', 4, 2, Status.CANCELLED),
                (customer2, cleaner2, 'Deep clean', 7, time(9, 30), '44 Church Street', 'Onehunga', '1061', 2, 2, Status.CONFIRMED),
            ]

            for customer, cleaner, service_name, offset, start_time, street, suburb, postcode, bedrooms, bathrooms, final_status in rows:
                service = services[service_name]
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
                    access_notes='',
                    total_price=service.price_for(bedrooms, bathrooms),
                    status=Status.PENDING,
                )
                booking.history.create(
                    from_status='',
                    to_status=Status.PENDING,
                    changed_by=customer,
                    note='Demo booking created.',
                )
                for next_status in ROUTES[final_status]:
                    booking.record_status(next_status, admin, note='Demo status update.')

        self.stdout.write(self.style.SUCCESS(
            f'{Service.objects.count()} services, {User.objects.count()} users and '
            f'{Booking.objects.count()} bookings are in the database.'
        ))
