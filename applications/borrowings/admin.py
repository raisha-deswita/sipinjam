from django.contrib import admin
from .models import Peminjaman, Pengembalian

@admin.register(Peminjaman)
class PeminjamanAdmin(admin.ModelAdmin):
    list_display = ('user', 'alat', 'jumlah', 'waktu_pinjam', 'waktu_kembali_rencana', 'status', 'denda_per_hari')
    list_filter = ('status', 'waktu_pinjam', 'waktu_kembali_rencana')
    search_fields = ('user__username', 'alat__nama_alat')
    date_hierarchy = 'waktu_pinjam'


@admin.register(Pengembalian)
class PengembalianAdmin(admin.ModelAdmin):
    list_display = ('peminjaman', 'petugas', 'waktu_kembali_realisasi', 'kondisi_akhir', 'terlambat', 'total_denda')
    
    list_filter = ('kondisi_akhir', 'waktu_kembali_realisasi')
    
    search_fields = ('peminjaman__user__username', 'peminjaman__alat__nama_alat')