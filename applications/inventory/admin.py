from django.contrib import admin
from .models import KategoriAlat, Alat

@admin.register(KategoriAlat)
class KategoriAlatAdmin(admin.ModelAdmin):
    list_display = ('nama_kategori', 'keterangan')
    search_fields = ('nama_kategori',)

@admin.register(Alat)
class AlatAdmin(admin.ModelAdmin):
    list_display = ('nama_alat', 'kategori', 'stok', 'kondisi', 'lokasi')
    list_filter = ('kategori', 'kondisi', 'lokasi')
    search_fields = ('nama_alat', 'lokasi')