from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView, View

from core.models import AuditLog

from .forms import EmailLoginForm, ProfileForm, SignUpForm, StaffUserForm, UserRolesForm
from .models import CUSTOMER

User = get_user_model()


class SignUpView(CreateView):
    """
    Public registration.

    Every account created here lands in the Customer group and nowhere else. Staff accounts are
    made by an administrator, so nobody can promote themselves by signing up.
    """

    form_class = SignUpForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('core:dashboard')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('core:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        group, _ = Group.objects.get_or_create(name=CUSTOMER)
        self.object.groups.add(group)
        login(self.request, self.object)
        messages.success(self.request, 'Your account is ready. Welcome to ServiceHub.')
        return response


class ThrottledLoginView(LoginView):
    """
    Django's login view with a failure counter on top.

    The counter is keyed on the submitted email rather than on the IP address, so it follows the
    account being attacked. An attacker rotating through addresses still hits the same lock, and
    a shared office IP does not lock out everyone in the building.
    """

    template_name = 'accounts/login.html'
    authentication_form = EmailLoginForm
    redirect_authenticated_user = True

    def cache_key(self):
        email = (self.request.POST.get('username') or '').strip().lower()
        return f'login-fail:{email}' if email else None

    def attempts(self):
        key = self.cache_key()
        return cache.get(key, 0) if key else 0

    def is_locked(self):
        return self.attempts() >= settings.LOGIN_MAX_ATTEMPTS

    def post(self, request, *args, **kwargs):
        if self.is_locked():
            form = self.get_form()
            form.add_error(None, 'Too many failed attempts. Try again in 15 minutes.')
            return self.form_invalid(form)
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        key = self.cache_key()
        if key and not self.is_locked():
            cache.set(key, self.attempts() + 1, settings.LOGIN_LOCKOUT_SECONDS)
            left = settings.LOGIN_MAX_ATTEMPTS - self.attempts()
            if 0 < left <= 2:
                form.add_error(
                    None, f'{left} attempt{"s" if left != 1 else ""} left before this account '
                          'is locked for 15 minutes.')
        return super().form_invalid(form)

    def form_valid(self, form):
        key = self.cache_key()
        if key:
            cache.delete(key)
        # Stops session fixation: whatever session id the browser arrived with is thrown away.
        self.request.session.cycle_key()
        return super().form_valid(form)


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """Edits request.user and nobody else, so there is no object to check."""

    form_class = ProfileForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('accounts:profile')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Your details have been updated.')
        return super().form_valid(form)


class UserListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'accounts.view_user'
    template_name = 'manage/user_list.html'
    context_object_name = 'users'
    paginate_by = 25

    def get_queryset(self):
        qs = User.objects.prefetch_related('groups')
        role = self.request.GET.get('role')
        if role:
            qs = qs.filter(groups__name=role)
        search = (self.request.GET.get('q') or '').strip()
        if search:
            qs = qs.filter(email__icontains=search) | qs.filter(last_name__icontains=search)
        return qs.distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['groups'] = Group.objects.all()
        ctx['role'] = self.request.GET.get('role', '')
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class StaffUserCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = 'accounts.add_user'
    form_class = StaffUserForm
    template_name = 'manage/staff_user_form.html'
    success_url = reverse_lazy('manage:users')

    def form_valid(self, form):
        response = super().form_valid(form)
        AuditLog.record(self.request.user, 'staff_user_created', 'User', self.object.email)
        messages.success(self.request, f'Created an account for {self.object.get_full_name()}.')
        return response


class UserRolesView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Grants and removes roles. Every change lands in the audit log."""

    permission_required = 'accounts.change_user'

    def get_target(self, pk):
        return get_object_or_404(User.objects.prefetch_related('groups'), pk=pk)

    def get(self, request, pk):
        target = self.get_target(pk)
        form = UserRolesForm(initial={'roles': target.groups.all()},
                             target=target, editor=request.user)
        return render(request, 'manage/user_roles.html', {'target': target, 'form': form})

    def post(self, request, pk):
        target = self.get_target(pk)
        form = UserRolesForm(request.POST, target=target, editor=request.user)
        if not form.is_valid():
            return render(request, 'manage/user_roles.html', {'target': target, 'form': form})

        before = set(target.groups.values_list('name', flat=True))
        target.groups.set(form.cleaned_data['roles'])
        after = set(target.groups.values_list('name', flat=True))
        for name in sorted(after - before):
            AuditLog.record(request.user, 'role_granted', 'User', f'{target.email}:{name}')
        for name in sorted(before - after):
            AuditLog.record(request.user, 'role_removed', 'User', f'{target.email}:{name}')

        messages.success(request, f'Roles updated for {target.get_full_name()}.')
        return redirect('manage:users')
