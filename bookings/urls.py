from django.urls import path

from . import views

app_name = 'bookings'

urlpatterns = [
    path('', views.MyBookingListView.as_view(), name='mine'),
    path('new/<slug:slug>/', views.BookingCreateView.as_view(), name='create'),
    # A UUID, not a sequential id. Nobody can find a valid booking by counting upwards.
    path('<uuid:pk>/', views.BookingDetailView.as_view(), name='detail'),
    path('<uuid:pk>/edit/', views.BookingUpdateView.as_view(), name='edit'),
    path('<uuid:pk>/cancel/', views.BookingCancelView.as_view(), name='cancel'),
]
