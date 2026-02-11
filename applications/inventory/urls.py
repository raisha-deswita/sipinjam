from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # URLS Kategori Alat
    path('kategori/', views.list_kategori, name='kategori_list'),
    path('kategori/add/', views.add_kategori, name='kategori_add'),
    path('kategori/edit/<int:pk>/', views.edit_kategori, name='kategori_edit'),
    path('kategori/delete/<int:pk>/', views.delete_kategori, name='kategori_delete'),

    # URLS Alat
    path('', views.list_alat, name='list'),
    path('add/', views.add_alat, name='add'),
    path('edit/<int:pk>/', views.edit_alat, name='edit'),
    path('delete/<int:pk>/', views.delete_alat, name='delete'),
    path('download-aset/', views.download_excel_alat, name='download_aset'),
]