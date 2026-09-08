from django.urls import path

from . import views

app_name = 'services'

urlpatterns = [
    path('', views.ServiceListView.as_view(), name='list'),
    # A slug, not an id. The catalogue is public, so a readable URL is worth more here than
    # an opaque one, and there is nothing private to enumerate.
    path('<slug:slug>/', views.ServiceDetailView.as_view(), name='detail'),
]
