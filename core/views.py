from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import redirect
from django.views.generic import ListView, TemplateView

from bookings.models import Booking, Status
from services.models import Service

from .models import AuditLog


class HomeView(TemplateView):
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['services'] = Service.objects.active()
        return ctx


class DashboardRouterView(LoginRequiredMixin, TemplateView):
    """
    One URL that sends each role to the right place.

    Having a single post-sign-in destination keeps the redirect logic in one readable place
    instead of scattering it through the sign-in view, the sign-up view and the password reset
    flow. Administrator is checked first because an administrator who is also a cleaner should
    land on the management screens.
    """

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.is_administrator:
            return redirect('manage:bookings')
        if user.is_cleaner:
            return redirect('staff:jobs')
        return redirect('bookings:mine')


class PrivacyView(TemplateView):
    template_name = 'core/privacy.html'


class TermsView(TemplateView):
    template_name = 'core/terms.html'


class AuditLogView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Read-only by construction.

    There is no update or delete route anywhere in the project, so the only way to change this
    table is to reach the database directly. That is the point of keeping it.
    """

    permission_required = 'core.view_auditlog'
    template_name = 'manage/audit_log.html'
    context_object_name = 'entries'
    paginate_by = 50

    def get_queryset(self):
        qs = AuditLog.objects.select_related('actor')
        action = self.request.GET.get('action')
        if action:
            qs = qs.filter(action=action)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['actions'] = (AuditLog.objects.values_list('action', flat=True)
                          .distinct().order_by('action'))
        ctx['action'] = self.request.GET.get('action', '')
        ctx['pending_count'] = Booking.objects.filter(status=Status.PENDING).count()
        return ctx
