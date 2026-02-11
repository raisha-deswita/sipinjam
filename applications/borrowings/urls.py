from django.urls import path
from . import views

app_name = 'borrowing'

urlpatterns = [
    path('', views.list_peminjaman, name='list'),
    path('add/', views.add_peminjaman, name='add'),
    path('kembali/<int:pk>/', views.kembalikan_alat, name='kembali'),
    path('approve/<int:pk>/', views.approve_peminjaman, name='approve'),
    path('reject/<int:pk>/', views.reject_peminjaman, name='reject'),
    path('download-laporan/', views.download_laporan, name='download_laporan'),
    path('download-denda/', views.download_laporan_denda, name='download_denda'),
    path('lunasi/<int:pk>/', views.lunasi_denda, name='lunasi'),
]