from django.urls import path
from app.views.auth_views import login_view, register_view, logout_view, onboarding_view

app_name = 'tenants'

urlpatterns = [
    path('', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
    path('onboarding/', onboarding_view, name='onboarding'),
]
