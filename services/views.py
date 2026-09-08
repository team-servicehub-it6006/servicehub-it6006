from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView, View

from core.models import AuditLog

from .models import Service


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['name', 'description', 'inclusions', 'base_price', 'duration_minutes',
                  'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'inclusions': forms.Textarea(attrs={'rows': 8}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault('class', 'form-check-input')
            else:
                field.widget.attrs.setdefault('class', 'form-control')


class ServiceListView(ListView):
    """Public catalogue. Inactive services are filtered out in the queryset, not the template."""

    template_name = 'services/service_list.html'
    context_object_name = 'services'

    def get_queryset(self):
        return Service.objects.active()


class ServiceDetailView(DetailView):
    template_name = 'services/service_detail.html'
    context_object_name = 'service'

    def get_queryset(self):
        # An inactive service gives 404 rather than a page, so a stale link cannot start a
        # booking for something the business no longer sells.
        return Service.objects.active()


class ManageServiceListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'services.change_service'
    template_name = 'manage/service_list.html'
    context_object_name = 'services'
    queryset = Service.objects.all()


class ServiceCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = 'services.add_service'
    model = Service
    form_class = ServiceForm
    template_name = 'manage/service_form.html'
    success_url = reverse_lazy('manage:services')

    def form_valid(self, form):
        response = super().form_valid(form)
        AuditLog.record(self.request.user, 'service_created', 'Service', self.object.slug)
        messages.success(self.request, f'Added {self.object.name}.')
        return response


class ServiceUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = 'services.change_service'
    model = Service
    form_class = ServiceForm
    template_name = 'manage/service_form.html'
    success_url = reverse_lazy('manage:services')

    def form_valid(self, form):
        response = super().form_valid(form)
        AuditLog.record(self.request.user, 'service_updated', 'Service', self.object.slug)
        messages.success(self.request, f'Updated {self.object.name}.')
        return response


class ServiceDeactivateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Delete, except it usually is not.

    A service with bookings against it is never removed, because deleting it would take the
    history of every job booked under it. It is deactivated instead, which hides it from
    customers and leaves the past intact. The screen says so rather than pretending the delete
    worked.
    """

    permission_required = 'services.delete_service'
    http_method_names = ['post']

    def post(self, request, slug):
        service = get_object_or_404(Service, slug=slug)
        if service.bookings.exists():
            service.is_active = False
            service.save(update_fields=['is_active'])
            AuditLog.record(request.user, 'service_deactivated', 'Service', service.slug)
            messages.warning(
                request,
                f'{service.name} has bookings against it, so it was deactivated rather than '
                'deleted. Customers can no longer book it and the old bookings are untouched.')
        else:
            AuditLog.record(request.user, 'service_deleted', 'Service', service.slug)
            name = service.name
            service.delete()
            messages.success(request, f'Deleted {name}.')
        return redirect('manage:services')
