from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('login/', views.ThrottledLoginView.as_view(), name='login'),
    # POST only. Django 5 enforces this, which stops a crafted image tag signing somebody out.
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile/', views.ProfileUpdateView.as_view(), name='profile'),

    path('password_change/', auth_views.PasswordChangeView.as_view(
        template_name='accounts/password_change.html',
        success_url='/accounts/password_change/done/'), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='accounts/password_change_done.html'), name='password_change_done'),

    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html',
        email_template_name='accounts/password_reset_email.txt',
        success_url='/accounts/password_reset/sent/'), name='password_reset'),
    path('password_reset/sent/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_sent.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url='/accounts/reset/done/'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'), name='password_reset_complete'),
]
