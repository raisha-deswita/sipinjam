from django.db import models
from django.conf import settings
from django.utils import timezone
from applications.inventory.models import Alat 
from django.core.exceptions import ValidationError

class Peminjaman(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Menunggu Persetujuan'),
        ('dipinjam', 'Sedang Dipinjam'),
        ('dikembalikan', 'Sudah Dikembalikan'),
        ('hilang', 'Hilang'),
        ('ditolak', 'Ditolak'),
    ]

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
    
    petugas = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='peminjaman_petugas'
    )

    jumlah = models.PositiveIntegerField(default=1)
    waktu_pinjam = models.DateTimeField(default=timezone.now)
    waktu_kembali_rencana = models.DateTimeField()
    
    denda_per_hari = models.PositiveIntegerField(default=0, help_text="Nominal denda per hari (snapshot)")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='dipinjam')
    catatan = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.pk: 
            self.denda_per_hari = self.alat.denda_per_hari
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.alat.nama_alat}"

    class Meta:
        verbose_name = "Peminjaman"
        verbose_name_plural = "Data Peminjaman"
        ordering = ['-waktu_pinjam']


class Pengembalian(models.Model):
    peminjaman = models.OneToOneField(
        Peminjaman,
        on_delete=models.CASCADE,
        related_name='detail_pengembalian'
    )
    
    petugas = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pengembalian_petugas'
    )

    waktu_kembali_realisasi = models.DateTimeField(auto_now_add=True)
    
    kondisi_akhir = models.CharField(
        max_length=20, 
        choices=[('baik', 'Baik'), ('rusak', 'Rusak'), ('hilang', 'Hilang')],
        default='baik'
    )

    biaya_kerusakan = models.PositiveIntegerField( 
        default=0,
        help_text="Biaya perbaikan jika barang rusak (diinput petugas)"
    )

    STATUS_BAYAR = [
        ('lunas', 'Lunas'),
        ('belum_lunas', 'Belum Lunas'),
    ]
    status_pembayaran = models.CharField(
        max_length=20, 
        choices=STATUS_BAYAR, 
        default='belum_lunas' 
    )

    catatan = models.TextField(
        blank=True, 
        null=True, 
        help_text="Detail kerusakan atau keterangan tambahan"
    )

    terlambat = models.IntegerField(default=0)
    total_denda = models.IntegerField(default=0)
    
    def __str__(self):
        return f"Pengembalian: {self.peminjaman.alat.nama_alat}"

    class Meta:
        verbose_name = "Pengembalian"
        verbose_name_plural = "Data Pengembalian"