from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import Group

from .models import ADMINISTRATOR, CLEANER

User = get_user_model()


class BootstrapMixin:
    """Adds the Bootstrap classes once instead of on every field definition."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
            field.widget.attrs.setdefault('class', css)


class SignUpForm(BootstrapMixin, UserCreationForm):
    """
    Public registration. It can only ever produce a customer.

    There is no role field here on purpose. If a visitor could choose their own role, the whole
    permission model would be decoration.
    """

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'suburb']
        labels = {'suburb': 'Suburb or city'}

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with that email address already exists.')
        return email


class EmailLoginForm(BootstrapMixin, AuthenticationForm):
    username = forms.EmailField(label='Email address')

    # Same message whichever half is wrong, so the form does not confirm which addresses are
    # registered.
    error_messages = {
        'invalid_login': 'That email address and password do not match an account.',
        'inactive': 'That email address and password do not match an account.',
    }


class ProfileForm(BootstrapMixin, forms.ModelForm):
    """A customer correcting their own details. IPP 7 of the Privacy Act, in practice."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'suburb']


class StaffUserForm(BootstrapMixin, UserCreationForm):
    """Administrators creating a cleaner or another administrator."""

    role = forms.ChoiceField(
        choices=[(CLEANER, 'Cleaner'), (ADMINISTRATOR, 'Administrator')],
        help_text='Cleaners see only the jobs assigned to them.')

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'suburb']

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with that email address already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=commit)
        group, _ = Group.objects.get_or_create(name=self.cleaned_data['role'])
        user.groups.add(group)
        return user


class UserRolesForm(forms.Form):
    """
    Changing what somebody is allowed to do.

    The check that an administrator cannot strip their own administrator role is a safety rule
    rather than a security one. It exists so that the business cannot lock itself out of its own
    system with one careless click, which is a mistake that is very easy to make and very
    annoying to undo.
    """

    roles = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False)

    def __init__(self, *args, target=None, editor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.target = target
        self.editor = editor

    def clean_roles(self):
        chosen = self.cleaned_data['roles']
        if self.target and self.editor and self.target.pk == self.editor.pk:
            if not any(g.name == ADMINISTRATOR for g in chosen):
                raise forms.ValidationError(
                    'You cannot remove your own administrator role. Ask another administrator '
                    'to do it if you really need to.')
        return chosen
