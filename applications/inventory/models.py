from django.db import models

class KategoriAlat(models.Model):
    nama_kategori = models.CharField(max_length=100)
    keterangan = models.TextField(blank=True, null=True)
    class Meta:
        verbose_name_plural = "Kategori Alat"

    def __str__(self):
        return self.nama_kategori


class Alat(models.Model):
    KONDISI_CHOICES = [
        ('baik', 'Baik'),
        ('rusak', 'Rusak'),
        ('hilang', 'Hilang'),
    ]

    kategori = models.ForeignKey(
        KategoriAlat, 
        on_delete=models.PROTECT,  
        related_name='list_alat'
    )
    
    nama_alat = models.CharField(max_length=150)
    stok = models.PositiveIntegerField(default=0)
    kondisi = models.CharField(max_length=20, choices=KONDISI_CHOICES, default='baik')
    lokasi = models.CharField(max_length=100, verbose_name="Lokasi Penyimpanan")
    denda_per_hari = models.IntegerField(default=0)
    denda_ganti_rugi = models.PositiveIntegerField(
        default=0, 
        help_text="Nominal harga ganti rugi jika barang hilang/rusak"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Alat"

    def __str__(self):
        return f"{self.nama_alat} (Stok: {self.stok})"