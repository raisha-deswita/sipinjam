from django import forms
from django.utils import timezone
from .models import Peminjaman, Pengembalian
from applications.inventory.models import Alat

class PeminjamanForm(forms.ModelForm):
    class Meta:
        model = Peminjaman
        fields = ['alat', 'jumlah', 'waktu_kembali_rencana', 'catatan']
        
        widgets = {
            'alat': forms.Select(attrs={'class': 'form-select select2'}),
            'jumlah': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'waktu_kembali_rencana': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'catatan': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_waktu_kembali_rencana(self):
        tanggal = self.cleaned_data['waktu_kembali_rencana']
        if hasattr(tanggal, 'date'):
            tanggal = tanggal.date()
             
        if tanggal < timezone.now().date():
            raise forms.ValidationError("Tanggal pengembalian tidak boleh di masa lalu!")
        return tanggal

    def clean(self):
        cleaned_data = super().clean()
        alat = cleaned_data.get('alat')
        jumlah = cleaned_data.get('jumlah')

        if alat and jumlah:
            if jumlah > alat.stok:
                raise forms.ValidationError(f"Stok tidak cukup! Stok tersedia: {alat.stok}")
        
        return cleaned_data


class PengembalianForm(forms.ModelForm):
    class Meta:
        model = Pengembalian
        fields = ['kondisi_akhir', 'biaya_kerusakan', 'catatan']
        
        widgets = {
            'kondisi_akhir': forms.Select(attrs={'class': 'form-select'}),
            'biaya_kerusakan': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'value': 0}),
            'catatan': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Catatan kerusakan (jika ada)...'}),
        }