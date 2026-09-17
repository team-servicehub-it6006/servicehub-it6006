"""
Everything a cleaner can reach.

Kept separate from the customer URLs so that the boundary is visible in the URL itself. A
cleaner has exactly two routes: the list of jobs assigned to them, and the button that moves
one of those jobs along.
"""
from django.urls import path

from . import views

app_name = 'staff'

urlpatterns = [
    path('jobs/', views.MyJobListView.as_view(), name='jobs'),
    path('jobs/<uuid:pk>/status/', views.JobStatusUpdateView.as_view(), name='job_status'),
]
