from django.db import models
from django.conf import settings
from django.utils import timezone
from applications.inventory.models import Alat 

class Peminjaman(models.Model):
    STATUS_CHOICES = [
        ('dipinjam', 'Sedang Dipinjam'),
        ('dikembalikan', 'Sudah Dikembalikan'),
        ('hilang', 'Hilang'),
    ]

    # Relasi
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, 
        related_name='peminjaman_user'
    )
    alat = models.ForeignKey(
        Alat,
        on_delete=models.CASCADE,
        related_name='peminjaman_alat'
    )
    # Petugas yang melayani peminjaman (Optional tapi bagus buat nilai plus)
    petugas = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='peminjaman_petugas'
    )

    # Data Transaksi
    jumlah = models.PositiveIntegerField(default=1)
    waktu_pinjam = models.DateTimeField(default=timezone.now)
    waktu_kembali_rencana = models.DateTimeField()
    
    # Snapshot Denda (Biar kalau harga denda naik, transaksi lama aman)
    denda_per_hari = models.PositiveIntegerField(default=5000, help_text="Nominal denda per hari")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='dipinjam')
    catatan = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.alat.nama_alat}"

    class Meta:
        verbose_name = "Peminjaman"
        verbose_name_plural = "Data Peminjaman"
        ordering = ['-waktu_pinjam']


class Pengembalian(models.Model):
    # OneToOne karena 1 Peminjaman cuma punya 1 Pengembalian
    peminjaman = models.OneToOneField(
        Peminjaman,
        on_delete=models.CASCADE,
        related_name='detail_pengembalian'
    )
    
    # Petugas yang menerima barang (Optional)
    petugas = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pengembalian_petugas'
    )

    waktu_kembali_realisasi = models.DateTimeField(auto_now_add=True)
    
    # Kondisi barang pas balik (PENTING buat inventory)
    kondisi_akhir = models.CharField(
        max_length=20, 
        choices=[('baik', 'Baik'), ('rusak', 'Rusak'), ('hilang', 'Hilang')],
        default='baik'
    )

    terlambat = models.IntegerField(default=0)
    total_denda = models.IntegerField(default=0)
    
    def __str__(self):
        return f"Pengembalian: {self.peminjaman.alat.nama_alat}"

    class Meta:
        verbose_name = "Pengembalian"
        verbose_name_plural = "Data Pengembalian"