from django.contrib.auth.models import AbstractUser, BaseUserManager, Group
from django.core.validators import RegexValidator
from django.db import models

CUSTOMER = 'Customer'
CLEANER = 'Cleaner'
ADMINISTRATOR = 'Administrator'
ROLES = (CUSTOMER, CLEANER, ADMINISTRATOR)

# Accepts the formats people actually type here: 021 123 4567, 0211234567, +64 21 123 4567,
# 09 555 1234. Deliberately loose about spaces and dashes and strict about everything else.
nz_phone = RegexValidator(
    regex=r'^(\+64[\s-]?|0)[2-9](\d[\s-]?){6,9}\d$',
    message='Enter a New Zealand phone number, for example 021 123 4567.',
)


class UserManager(BaseUserManager):
    """
    Email is the login field, so the manager builds users from an email rather than a username.

    It has to subclass BaseUserManager, not plain Manager, because the authentication backend
    calls get_by_natural_key on it. A plain Manager looks fine until the first sign-in attempt.
    """

    use_in_migrations = True

    def _create(self, email, password, **extra):
        if not email:
            raise ValueError('An email address is required.')
        user = self.model(email=self.normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    @classmethod
    def normalize_email(cls, email):
        # Django's own version only lower-cases the domain. We lower-case the whole thing so
        # that Himani@example.com and himani@example.com cannot become two accounts.
        return super().normalize_email(email or '').strip().lower()

    def create_user(self, email, password=None, **extra):
        extra.setdefault('is_staff', False)
        extra.setdefault('is_superuser', False)
        return self._create(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        if not extra['is_staff'] or not extra['is_superuser']:
            raise ValueError('A superuser must have is_staff and is_superuser set.')
        user = self._create(email, password, **extra)
        group, _ = Group.objects.get_or_create(name=ADMINISTRATOR)
        user.groups.add(group)
        return user


class User(AbstractUser):
    """
    One table for customers, cleaners and administrators. The role is held through group
    membership rather than a role column, so a person can hold more than one if the business
    ever needs it and so permissions stay attached to the group.
    """
    username = None
    email = models.EmailField('email address', unique=True)
    first_name = models.CharField(max_length=60)
    last_name = models.CharField(max_length=60)
    phone = models.CharField(max_length=20, validators=[nz_phone])
    suburb = models.CharField(max_length=80, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    class Meta:
        ordering = ['first_name', 'last_name']

    def save(self, *args, **kwargs):
        # Two accounts must not be able to differ only by capitalisation.
        self.email = self.email.strip().lower()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.get_full_name()} <{self.email}>'

    def short_name(self):
        return f'{self.first_name} {self.last_name[:1]}.'.strip()

    @property
    def role_names(self):
        return list(self.groups.values_list('name', flat=True))

    def in_role(self, name):
        return self.groups.filter(name=name).exists()

    @property
    def is_customer(self):
        return self.in_role(CUSTOMER)

    @property
    def is_cleaner(self):
        return self.in_role(CLEANER)

    @property
    def is_administrator(self):
        return self.is_superuser or self.in_role(ADMINISTRATOR)
