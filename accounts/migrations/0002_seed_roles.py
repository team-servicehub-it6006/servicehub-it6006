"""
Creates the three roles and attaches their permissions.

This is a migration rather than a script or a fixture so that every developer's database, the
test database and production all end up with exactly the same roles. A role that exists on one
machine and not another is the kind of difference that hides an authorisation bug until a
marker finds it.
"""
from django.apps import apps as global_apps
from django.contrib.auth.management import create_permissions
from django.db import migrations

# Permissions are granted to the group. Never to a person. That way the answer to "who can do
# this?" is always one lookup, and revoking is one change instead of an audit of every account.
ROLE_PERMISSIONS = {
    'Customer': [
        ('services', 'view_service'),
        ('bookings', 'add_booking'),
        ('bookings', 'view_booking'),
        ('bookings', 'change_booking'),
    ],
    'Cleaner': [
        ('services', 'view_service'),
        ('bookings', 'view_booking'),
        # Lets a cleaner move a job along. It does not say which job: that is the object-level
        # check in the view, because every cleaner holds this same permission.
        ('bookings', 'update_job_status'),
    ],
    'Administrator': [
        ('services', 'view_service'),
        ('services', 'add_service'),
        ('services', 'change_service'),
        ('services', 'delete_service'),
        ('bookings', 'view_booking'),
        ('bookings', 'add_booking'),
        ('bookings', 'change_booking'),
        ('bookings', 'view_all_bookings'),
        ('bookings', 'assign_cleaner'),
        ('bookings', 'update_job_status'),
        ('accounts', 'view_user'),
        ('accounts', 'add_user'),
        ('accounts', 'change_user'),
        ('core', 'view_auditlog'),
    ],
}


def ensure_permissions():
    """
    Django creates the default model permissions in a post_migrate signal, which fires after
    every migration has run. That is too late for a data migration that wants to hand them out,
    so we ask for them early. Without this the migration works on a database that already has
    the rows and fails on a fresh one, which is the worst kind of bug to find later.
    """
    for label in ('services', 'bookings', 'accounts', 'core'):
        app_config = global_apps.get_app_config(label)
        app_config.models_module = app_config.models_module or True
        create_permissions(app_config, verbosity=0)


def seed(apps, schema_editor):
    ensure_permissions()
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    for role, wanted in ROLE_PERMISSIONS.items():
        group, _ = Group.objects.get_or_create(name=role)
        perms = []
        for app_label, codename in wanted:
            try:
                perms.append(Permission.objects.get(
                    content_type__app_label=app_label, codename=codename))
            except Permission.DoesNotExist:
                # Never silently skip. A missing permission here means a rename went through
                # without this list being updated, and the role would quietly lose an ability.
                raise RuntimeError(f'Permission {app_label}.{codename} does not exist.')
        group.permissions.set(perms)


def unseed(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name__in=ROLE_PERMISSIONS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('services', '0001_initial'),
        ('bookings', '0001_initial'),
        ('core', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
