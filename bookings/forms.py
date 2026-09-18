from datetime import datetime, timedelta

from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import CLEANER

from .models import Booking, Status

User = get_user_model()

MAX_DAYS_AHEAD = 90


class BookingForm(forms.ModelForm):
    """
    The main customer form.

    Everything here is checked on the server. The browser's own date picker and required
    attributes are a convenience for the person filling the form in, and are treated as worth
    nothing at all once the request arrives.
    """

    class Meta:
        model = Booking
        fields = ['scheduled_date', 'scheduled_time', 'street_address', 'suburb', 'postcode',
                  'bedrooms', 'bathrooms', 'access_notes']
        widgets = {
            'scheduled_date': forms.DateInput(attrs={'type': 'date'}),
            'scheduled_time': forms.TimeInput(attrs={'type': 'time'}),
            'access_notes': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'access_notes': 'Access notes for the cleaner (optional)',
        }
        help_texts = {
            'access_notes': 'Only if you need to. The maintenance command clears this 30 days after completion or cancellation.',
        }

    def __init__(self, *args, service=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = service
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean_scheduled_date(self):
        date = self.cleaned_data['scheduled_date']
        if date < timezone.localdate():
            raise forms.ValidationError('A booking cannot be in the past.')
        if date > timezone.localdate() + timedelta(days=MAX_DAYS_AHEAD):
            raise forms.ValidationError(
                f'Bookings can be made up to {MAX_DAYS_AHEAD} days ahead.')
        return date

    def clean_scheduled_time(self):
        time = self.cleaned_data['scheduled_time']
        if not (7 <= time.hour < 19):
            raise forms.ValidationError('Cleans start between 7:00am and 7:00pm.')
        return time

    def clean_postcode(self):
        postcode = self.cleaned_data['postcode'].strip()
        if not postcode.isdigit() or len(postcode) != 4:
            raise forms.ValidationError('Enter a four digit New Zealand postcode.')
        return postcode

    def clean_street_address(self):
        address = self.cleaned_data['street_address'].strip()
        if len(address) < 5:
            raise forms.ValidationError('Enter the full street address, including the number.')
        return address

    def clean(self):
        cleaned = super().clean()
        if self.service and not self.service.is_active:
            raise forms.ValidationError('That service is no longer available.')

        date = cleaned.get('scheduled_date')
        time = cleaned.get('scheduled_time')
        if date and time and date == timezone.localdate():
            start = timezone.make_aware(datetime.combine(date, time),
                                        timezone.get_current_timezone())
            if start < timezone.now() + timedelta(hours=2):
                raise forms.ValidationError(
                    'Same-day bookings need at least two hours notice.')
        return cleaned


class AssignCleanerForm(forms.Form):
    """
    Assigning a cleaner to a job.

    Two rules matter. The choices come from the Cleaner group, resolved when the form is built
    rather than stored on the model, because group membership changes. And a cleaner cannot be
    given two jobs that overlap, which is the mistake the spreadsheet used to make every week.
    """

    cleaner = forms.ModelChoiceField(queryset=User.objects.none(), label='Cleaner')
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 2}),
                           label='Note (optional)')

    def __init__(self, *args, booking=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.booking = booking
        self.fields['cleaner'].queryset = User.objects.filter(
            groups__name=CLEANER, is_active=True).order_by('first_name')
        self.fields['cleaner'].widget.attrs['class'] = 'form-select'
        self.fields['note'].widget.attrs['class'] = 'form-control'

    def clean_cleaner(self):
        cleaner = self.cleaned_data['cleaner']
        if not self.booking:
            return cleaner

        if not self.booking.is_editable:
            raise forms.ValidationError('Only pending or confirmed bookings can be assigned.')

        start, end = self.booking.starts_at, self.booking.ends_at
        for job in (Booking.objects
                    .filter(cleaner=cleaner, scheduled_date=self.booking.scheduled_date)
                    .exclude(pk=self.booking.pk)
                    .exclude(status__in=[Status.CANCELLED, Status.COMPLETED])
                    .select_related('service')):
            if job.starts_at < end and start < job.ends_at:
                raise forms.ValidationError(
                    f'{cleaner.short_name()} is already on {job.reference} from '
                    f'{job.scheduled_time:%H:%M} to {job.ends_at:%H:%M} that day.')
        return cleaner


class StatusUpdateForm(forms.Form):
    """
    Used by the cleaner buttons and by the administrator's status control.

    The submitted status is checked against the transition table on the model. There is no path
    through this form that lets a status be set to something the business does not allow, even
    if the request is built by hand with a value the buttons never offer.
    """

    status = forms.ChoiceField(choices=Status.choices)
    note = forms.CharField(required=False)

    def __init__(self, *args, booking=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.booking = booking

    def clean_status(self):
        new_status = self.cleaned_data['status']
        if self.booking and not self.booking.can_transition_to(new_status):
            raise forms.ValidationError(
                f'A booking cannot go from {self.booking.get_status_display()} to '
                f'{dict(Status.choices).get(new_status, new_status)}.')
        return new_status
