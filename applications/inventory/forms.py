from django import forms
from .models import Alat, KategoriAlat

class KategoriForm(forms.ModelForm):
    class Meta:
        model = KategoriAlat
        fields = ['nama_kategori', 'keterangan']
        
        widgets = {
            'nama_kategori': forms.TextInput(attrs={'class': 'form-control'}),
            'keterangan': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class AlatForm(forms.ModelForm):
    class Meta:
        model = Alat
        fields = ['nama_alat', 'kategori', 'stok', 'kondisi', 'lokasi', 'denda_per_hari', 'denda_ganti_rugi']
        widgets = {
            'nama_alat': forms.TextInput(attrs={'class': 'form-control'}),
            'kategori': forms.Select(attrs={'class': 'form-select'}),
            'stok': forms.NumberInput(attrs={'class': 'form-control'}),
            'kondisi': forms.Select(attrs={'class': 'form-select'}),
            'lokasi': forms.TextInput(attrs={'class': 'form-control'}),
            'denda_per_hari': forms.NumberInput(attrs={'class': 'form-control'}),
            'denda_ganti_rugi': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def clean_stok(self):
        stok = self.cleaned_data.get('stok')
        if stok < 0:
            raise forms.ValidationError("Stok tidak boleh negatif!")
        return stok