"""
Everything an administrator can reach, in one place.

Keeping the whole management surface in a single URLconf was a deliberate choice. It means the
answer to "what can an administrator do that nobody else can" is one file long, and a new route
added in the wrong place stands out in review. Every view listed here carries its own permission
check; grouping them does not grant anything on its own.
"""
from django.urls import path

from accounts import views as account_views
from bookings import views as booking_views
from services import views as service_views

from . import views as core_views

app_name = 'manage'

urlpatterns = [
    path('bookings/', booking_views.ManageBookingListView.as_view(), name='bookings'),
    path('bookings/<uuid:pk>/assign/', booking_views.AssignCleanerView.as_view(), name='assign'),

    path('services/', service_views.ManageServiceListView.as_view(), name='services'),
    path('services/new/', service_views.ServiceCreateView.as_view(), name='service_create'),
    path('services/<slug:slug>/edit/', service_views.ServiceUpdateView.as_view(),
         name='service_edit'),
    path('services/<slug:slug>/delete/', service_views.ServiceDeactivateView.as_view(),
         name='service_delete'),

    path('users/', account_views.UserListView.as_view(), name='users'),
    path('users/new/', account_views.StaffUserCreateView.as_view(), name='user_create'),
    # The only integer id in a URL anywhere in the project. The page is administrator-only and
    # an administrator can already see every user, so there is nothing here to enumerate.
    path('users/<int:pk>/roles/', account_views.UserRolesView.as_view(), name='user_roles'),

    path('audit/', core_views.AuditLogView.as_view(), name='audit'),
]
