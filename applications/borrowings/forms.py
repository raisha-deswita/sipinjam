from django import forms
from django.utils import timezone
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Div, HTML
from django.urls import reverse_lazy
from .models import Peminjaman, Pengembalian
from applications.inventory.models import Alat

class PeminjamanForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

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
        tanggal = self.cleaned_data.get('waktu_kembali_rencana')
        if hasattr(tanggal, 'date'):
            tanggal = tanggal.date()
             
        if tanggal and tanggal < timezone.now().date():
            raise forms.ValidationError("Tanggal pengembalian tidak boleh di masa lalu!")
        return tanggal

    def clean(self):
        cleaned_data = super().clean()
        alat = cleaned_data.get('alat')
        jumlah = cleaned_data.get('jumlah')

        if self.user:
            active_loan = Peminjaman.objects.filter(
                user=self.user,
                status__in=['pending', 'dipinjam']
            ).exists()
            
            if active_loan:
                raise forms.ValidationError(
                    "Gagal! Anda masih memiliki peminjaman yang sedang aktif atau menunggu persetujuan."
                )

        if alat and jumlah:
            if jumlah > alat.stok:
                raise forms.ValidationError(f"Stok tidak cukup! Stok tersedia: {alat.stok}")
        
        return cleaned_data

class PengembalianForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        # Default to 0 or None so it doesn't become the string "None"
        peminjaman_id = kwargs.pop('peminjaman_id', 0) 
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_tag = False 
        self.helper.layout = Layout(
            Div(
                Field('kondisi_akhir', 
                      hx_get=reverse_lazy('borrowing:check_kondisi'),
                      hx_target="#update-area",
                      # hx_include tells HTMX to grab the hidden ID input
                      hx_include="[name='peminjaman_id']"), 
                css_class="mb-3"
            ),
            Div(id="update-area"), 
            Div(Field('catatan', rows="3"), css_class="mb-3"),
            # Ensure the value is definitely an integer
            HTML(f'<input type="hidden" name="peminjaman_id" value="{int(peminjaman_id)}">')
        )

    class Meta:
        model = Pengembalian
        fields = ['kondisi_akhir', 'catatan'] # Removed biaya_kerusakan from here!