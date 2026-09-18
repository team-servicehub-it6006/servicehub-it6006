from django.contrib import messages
from django.contrib.auth.mixins import (LoginRequiredMixin, PermissionRequiredMixin,
                                        UserPassesTestMixin)
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import DetailView, ListView, View

from core.models import AuditLog
from services.models import Service

from .forms import AssignCleanerForm, BookingForm, StatusUpdateForm
from .models import Booking, Status


class ObjectAccessMixin(UserPassesTestMixin):
    """
    The object-level half of the authorisation check.

    A role is not enough on its own. Every cleaner holds the same permission, so without this
    any cleaner could open any job by changing the UUID in the address bar. Booking.visible_to
    is the single place that answers the question, and both this mixin and the tests use it.
    """

    def test_func(self):
        return self.get_object().visible_to(self.request.user)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()   # send them to the sign-in page
        raise PermissionDenied                      # signed in but refused: 403, not 404


class MyBookingListView(LoginRequiredMixin, ListView):
    """The customer's own bookings. Filtered in the queryset, never in the template."""

    template_name = 'bookings/my_bookings.html'
    context_object_name = 'bookings'
    paginate_by = 20

    def get_queryset(self):
        return (Booking.objects.for_customer(self.request.user)
                .select_related('service', 'cleaner'))


class BookingCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'bookings.add_booking'

    def get_service(self, slug):
        return get_object_or_404(Service.objects.active(), slug=slug)

    def get(self, request, slug):
        service = self.get_service(slug)
        return render(request, 'bookings/booking_form.html', {
            'service': service,
            'form': BookingForm(service=service, initial={'bedrooms': 2, 'bathrooms': 1}),
        })

    def post(self, request, slug):
        service = self.get_service(slug)
        form = BookingForm(request.POST, service=service)
        if not form.is_valid():
            return render(request, 'bookings/booking_form.html',
                          {'service': service, 'form': form})

        booking = form.save(commit=False)
        # Both of these come from the server, never from the form. A customer cannot book on
        # somebody else's behalf and cannot choose their own price.
        booking.customer = request.user
        booking.service = service
        booking.total_price = service.price_for(booking.bedrooms, booking.bathrooms)
        booking.status = Status.PENDING
        booking.save()
        booking.history.create(from_status='', to_status=Status.PENDING,
                               changed_by=request.user, note='Created by the customer.')
        messages.success(request, f'Booking {booking.reference} created. We will confirm it '
                                  'once a cleaner is assigned.')
        return redirect(booking.get_absolute_url())


class BookingDetailView(LoginRequiredMixin, ObjectAccessMixin, DetailView):
    """Same page for all three roles. The action panel is rendered by permission."""

    model = Booking
    template_name = 'bookings/booking_detail.html'
    context_object_name = 'booking'

    def get_queryset(self):
        return Booking.objects.select_related('service', 'customer', 'cleaner')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        booking = self.object
        user = self.request.user
        ctx['history'] = booking.history.select_related('changed_by')
        ctx['is_owner'] = booking.customer_id == user.id
        ctx['is_assigned_cleaner'] = booking.cleaner_id == user.id
        ctx['can_manage'] = user.has_perm('bookings.view_all_bookings')
        return ctx


class BookingUpdateView(LoginRequiredMixin, ObjectAccessMixin, View):
    """
    Editing is the owner's, and only while the job has not started.

    Two separate checks: ObjectAccessMixin says whether you may see it at all, then the status
    check says whether it is still changeable. Being allowed to read a record is not the same
    as being allowed to change it.
    """

    def get_booking(self, pk):
        booking = get_object_or_404(Booking.objects.select_related('service'), pk=pk)
        is_owner = booking.customer_id == self.request.user.id
        can_manage = (self.request.user.has_perm('bookings.view_all_bookings')
                      and self.request.user.has_perm('bookings.change_booking'))
        if not (is_owner or can_manage):
            raise PermissionDenied
        if not booking.is_editable:
            raise PermissionDenied
        return booking

    def get_object(self):
        return get_object_or_404(Booking, pk=self.kwargs['pk'])

    def get(self, request, pk):
        booking = self.get_booking(pk)
        return render(request, 'bookings/booking_form.html', {
            'service': booking.service, 'booking': booking,
            'form': BookingForm(instance=booking, service=booking.service),
        })

    def post(self, request, pk):
        booking = self.get_booking(pk)
        form = BookingForm(request.POST, instance=booking, service=booking.service)
        if not form.is_valid():
            return render(request, 'bookings/booking_form.html', {
                'service': booking.service, 'booking': booking, 'form': form})
        updated = form.save(commit=False)
        updated.total_price = booking.service.price_for(updated.bedrooms, updated.bathrooms)
        if updated.cleaner_id:
            availability = AssignCleanerForm(
                {'cleaner': updated.cleaner_id}, booking=updated)
            if not availability.is_valid():
                for error in availability.errors.get('cleaner', []):
                    form.add_error(None, error)
                return render(request, 'bookings/booking_form.html', {
                    'service': booking.service, 'booking': booking, 'form': form})
        updated.save()
        actor = 'administrator' if request.user.has_perm('bookings.view_all_bookings') else 'customer'
        updated.history.create(from_status=updated.status, to_status=updated.status,
                               changed_by=request.user, note=f'Details changed by the {actor}.')
        messages.success(request, f'Booking {updated.reference} updated.')
        return redirect(updated.get_absolute_url())


class BookingCancelView(LoginRequiredMixin, ObjectAccessMixin, View):
    """GET shows a confirmation page. Only POST actually cancels."""

    def get_object(self):
        return get_object_or_404(Booking, pk=self.kwargs['pk'])

    def get_booking(self, pk):
        booking = get_object_or_404(Booking, pk=pk)
        is_owner = booking.customer_id == self.request.user.id
        can_manage = (self.request.user.has_perm('bookings.view_all_bookings')
                      and self.request.user.has_perm('bookings.change_booking'))
        if not (is_owner or can_manage):
            raise PermissionDenied
        if not booking.is_editable or not booking.can_transition_to(Status.CANCELLED):
            raise PermissionDenied
        return booking

    def get(self, request, pk):
        return render(request, 'bookings/booking_cancel.html',
                      {'booking': self.get_booking(pk)})

    def post(self, request, pk):
        booking = self.get_booking(pk)
        booking.record_status(Status.CANCELLED, request.user,
                              note=request.POST.get('note', '')[:500])
        messages.success(request, f'Booking {booking.reference} has been cancelled.')
        if request.user.has_perm('bookings.view_all_bookings'):
            return redirect('manage:bookings')
        return redirect('bookings:mine')


class MyJobListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """A cleaner's own jobs. The queryset is the access control."""

    permission_required = 'bookings.update_job_status'
    template_name = 'bookings/my_jobs.html'
    context_object_name = 'jobs'
    paginate_by = 25

    def get_queryset(self):
        return (Booking.objects.for_cleaner(self.request.user)
                .exclude(status=Status.CANCELLED)
                .select_related('service', 'customer')
                .order_by('scheduled_date', 'scheduled_time'))


class JobStatusUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    A cleaner moving their own job along.

    Three things have to hold: the permission, the job being theirs, and the transition being
    legal. The buttons on the page only ever offer legal moves, but the check is here because
    the buttons are not what the server receives.
    """

    permission_required = 'bookings.update_job_status'
    http_method_names = ['post']

    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        is_admin = request.user.has_perm('bookings.view_all_bookings')
        if booking.cleaner_id != request.user.id and not is_admin:
            raise PermissionDenied

        form = StatusUpdateForm(request.POST, booking=booking)
        if not form.is_valid():
            for error in form.errors.get('status', ['That status change is not allowed.']):
                messages.error(request, error)
            return redirect(booking.get_absolute_url())

        if not is_admin and form.cleaned_data['status'] not in {
                Status.IN_PROGRESS, Status.COMPLETED}:
            raise PermissionDenied

        booking.record_status(form.cleaned_data['status'], request.user,
                              note=form.cleaned_data.get('note', ''))
        messages.success(request,
                         f'{booking.reference} is now {booking.get_status_display().lower()}.')

        # A "next" value out of a form is attacker-controlled, so it is checked against this
        # host before it is used. Otherwise it is an open redirect wearing a helpful hat.
        nxt = request.POST.get('next', '')
        if nxt and url_has_allowed_host_and_scheme(
                nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
            return redirect(nxt)
        return redirect('staff:jobs')


class ManageBookingListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'bookings.view_all_bookings'
    template_name = 'manage/booking_list.html'
    context_object_name = 'bookings'
    paginate_by = 30

    def get_queryset(self):
        qs = Booking.objects.select_related('service', 'customer', 'cleaner')
        status = self.request.GET.get('status')
        if status in dict(Status.choices):
            qs = qs.filter(status=status)
        search = (self.request.GET.get('q') or '').strip()
        if search:
            qs = qs.filter(Q(reference__icontains=search)
                           | Q(customer__first_name__icontains=search)
                           | Q(customer__last_name__icontains=search)
                           | Q(customer__email__icontains=search))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['statuses'] = Status.choices
        ctx['status'] = self.request.GET.get('status', '')
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class AssignCleanerView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'bookings.assign_cleaner'

    def get_booking(self, pk):
        booking = get_object_or_404(
            Booking.objects.select_related('service', 'customer', 'cleaner'), pk=pk)
        if booking.status in {Status.COMPLETED, Status.CANCELLED}:
            raise PermissionDenied
        return booking

    def get(self, request, pk):
        booking = self.get_booking(pk)
        form = AssignCleanerForm(booking=booking,
                                 initial={'cleaner': booking.cleaner_id})
        return render(request, 'manage/assign_cleaner.html',
                      {'booking': booking, 'form': form})

    def post(self, request, pk):
        booking = self.get_booking(pk)
        form = AssignCleanerForm(request.POST, booking=booking)
        if not form.is_valid():
            return render(request, 'manage/assign_cleaner.html',
                          {'booking': booking, 'form': form})

        booking.cleaner = form.cleaned_data['cleaner']
        booking.save(update_fields=['cleaner', 'updated_at'])
        AuditLog.record(request.user, 'cleaner_assigned', 'Booking',
                        f'{booking.reference}:{booking.cleaner.email}')

        if booking.can_transition_to(Status.CONFIRMED):
            booking.record_status(Status.CONFIRMED, request.user,
                                  note=f'Assigned to {booking.cleaner.short_name()}.')
        else:
            booking.history.create(from_status=booking.status, to_status=booking.status,
                                   changed_by=request.user,
                                   note=f'Reassigned to {booking.cleaner.short_name()}.')

        messages.success(request, f'{booking.reference} assigned to '
                                  f'{booking.cleaner.get_full_name()}.')
        return redirect(reverse('manage:bookings'))
