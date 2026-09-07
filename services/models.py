from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class ServiceQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class Service(models.Model):
    """One thing the business sells, such as a deep clean."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    description = models.TextField(help_text='Short summary shown on the catalogue card.')
    inclusions = models.TextField(help_text='One item per line. Shown on the detail page.')
    base_price = models.DecimalField(
        max_digits=8, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Price for a standard two bedroom, one bathroom property.')
    duration_minutes = models.PositiveIntegerField(
        validators=[MinValueValidator(30)],
        help_text='Used to work out whether two jobs for the same cleaner overlap.')
    is_active = models.BooleanField(
        default=True,
        help_text='Inactive services disappear from the catalogue but old bookings keep working.')
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ServiceQuerySet.as_manager()

    class Meta:
        ordering = ['base_price']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:110]
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('services:detail', args=[self.slug])

    def inclusion_list(self):
        return [line.strip() for line in self.inclusions.splitlines() if line.strip()]

    def duration_display(self):
        hours, minutes = divmod(self.duration_minutes, 60)
        if hours and minutes:
            return f'{hours}h {minutes}m'
        return f'{hours}h' if hours else f'{minutes}m'

    def price_for(self, bedrooms, bathrooms):
        """
        The price the customer is actually charged.

        Always calculated here, on the server, from the service and the property size. The
        booking form never reads a price from the submitted data, so editing the hidden field
        in the browser achieves nothing.
        """
        extra_bedrooms = max(0, int(bedrooms) - 2)
        extra_bathrooms = max(0, int(bathrooms) - 1)
        return (self.base_price
                + Decimal('25.00') * extra_bedrooms
                + Decimal('30.00') * extra_bathrooms)
