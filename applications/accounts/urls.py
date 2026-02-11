from django.urls import path
from django.contrib.auth import views as auth_views
from .views import dashboard
from . import views

urlpatterns = [
    path("dashboard/", dashboard, name="dashboard"),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
    path('register/', views.register_siswa, name='register'),
    path('add-petugas/', views.add_petugas, name='add_petugas'),
]
