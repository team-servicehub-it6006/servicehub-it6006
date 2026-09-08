from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    # One destination after sign-in that routes by role, rather than three different
    # success_urls scattered through the auth views.
    path('dashboard/', views.DashboardRouterView.as_view(), name='dashboard'),
    path('privacy/', views.PrivacyView.as_view(), name='privacy'),
    path('terms/', views.TermsView.as_view(), name='terms'),
]
