"""Cleaner routes, separate from customer booking URLs."""

from django.urls import path

from . import views

app_name = 'staff'

urlpatterns = [
    path('jobs/', views.MyJobListView.as_view(), name='jobs'),
    path('jobs/<uuid:pk>/status/', views.JobStatusUpdateView.as_view(), name='job_status'),
]
