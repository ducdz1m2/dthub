from django.urls import path
from .views import *
from django.contrib.auth import views as auth_views
urlpatterns = [
    path("auth/", auth_view, name="auth"),
    path("logout/", logout_view, name="logout"),
    path('profile/', profile_view, name='profile'),
    path('update-location/', update_location, name='update_location'),
    path('staff/', manage_staff_list, name='manage_staff_list'),
    path('staff/create/', create_staff_view, name='create_staff_view'),
    path('staff/edit/<int:staff_id>/', edit_staff, name='edit_staff'),
    path('staff/toggle/<int:staff_id>/', toggle_staff_status, name='toggle_staff_status'),
    path('staff/delete/<int:staff_id>/', delete_staff, name='delete_staff'),
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(template_name='accounts/password_reset.html'), 
         name='password_reset'),

    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(template_name='accounts/password_reset_done.html'), 
         name='password_reset_done'),

    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name='accounts/password_reset_confirm.html'), 
         name='password_reset_confirm'),

    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'), 
         name='password_reset_complete'),
]
