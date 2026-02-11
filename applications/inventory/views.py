from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from applications.accounts.decorators import role_required
from applications.activitylog.utils import log_activity
import csv
from django.http import HttpResponse
from django.utils import timezone
from .models import Alat, KategoriAlat
from .forms import AlatForm, KategoriForm

# CRUD Kategori Alat
# read/show
@login_required
def list_kategori(request):
    kategoris = KategoriAlat.objects.all()
    context = {
        'kategoris': kategoris,
        'title': 'Daftar Kategori'
    }
    return render(request, 'inventory/kategori_list.html', context)

# create
@login_required
@role_required(allowed_roles=['admin', 'petugas'])
def add_kategori(request):
    if request.method == 'POST':
        form = KategoriForm(request.POST)
        if form.is_valid():
            kategori = form.save()
            log_activity(request.user, f"Menambahkan kategori: {kategori.nama_kategori}")
            return redirect('inventory:kategori_list')
    else:
        form = KategoriForm()
    
    return render(request, 'inventory/form.html', {'form': form, 'title': 'Tambah Kategori'})

# update
@login_required
@role_required(allowed_roles=['admin', 'petugas'])
def edit_kategori(request, pk):
    kategori = get_object_or_404(KategoriAlat, pk=pk)
    if request.method == 'POST':
        form = KategoriForm(request.POST, instance=kategori)
        if form.is_valid():
            kategori = form.save()
            log_activity(request.user, f"Memperbarui kategori: {kategori.nama_kategori}")
            return redirect('inventory:kategori_list')
    else:
        form = KategoriForm(instance=kategori)
    
    return render(request, 'inventory/form.html', {'form': form, 'title': 'Edit Kategori'})

# delete
@login_required
@role_required(allowed_roles=['admin'])
def delete_kategori(request, pk):
    kategori = get_object_or_404(KategoriAlat, pk=pk)
    try:
        kategori.delete()
        log_activity(request.user, f"Menghapus kategori: {kategori.nama_kategori}")
    except:
        pass
    return redirect('inventory:kategori_list')


# CRUD Alat
# read/show
@login_required
def list_alat(request):
    alats = Alat.objects.all()
    return render(request, 'inventory/list.html', {'alats': alats, 'title': 'Daftar Alat'})

# save/create
@login_required
@role_required(['admin', 'petugas'])
def add_alat(request):
    if request.method == 'POST':
        form = AlatForm(request.POST)
        if form.is_valid():
            alat = form.save()
            log_activity(request.user, f"Menambahkan alat: {alat.nama_alat}")
            return redirect('inventory:list')
    else:
        form = AlatForm()
    return render(request, 'inventory/form.html', {'form': form, 'title': 'Tambah Alat'})

# delete
@login_required
@role_required(['admin'])
def delete_alat(request, pk):
    alat = get_object_or_404(Alat, pk=pk)
    nama_alat = alat.nama_alat
    alat.delete()
    log_activity(request.user, f"Menghapus alat: {alat.nama_alat}")
    return redirect('inventory:list')

# update
@login_required
@role_required(allowed_roles=['admin', 'petugas'])
def edit_alat(request, pk):
    alat = get_object_or_404(Alat, pk=pk)

    if request.method == 'POST':
        form = AlatForm(request.POST, instance=alat)
        if form.is_valid():
            alat = form.save()
            log_activity(request.user, f"Memperbarui alat: {alat.nama_alat}")
            return redirect('inventory:list')
    else:
        form = AlatForm(instance=alat)

    context = {
        'form': form,
        'title': f'Edit Barang: {alat.nama_alat}'
    }
    return render(request, 'inventory/form.html', context)

# download csv untuk laporan stok/barang
@login_required
@role_required(['admin', 'petugas'])
def download_excel_alat(request):
    response = HttpResponse(content_type='text/csv')
    filename = f"laporan_aset_sekolah_{timezone.now().date()}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Kode Alat', 'Nama Alat', 'Kategori', 'Stok Total', 'Stok Tersedia', 'Kondisi', 'Lokasi', 'Harga Satuan', 'Total Nilai Aset'])

    alat_list = Alat.objects.select_related('kategori').all().order_by('kategori', 'nama_alat')

    for alat in alat_list:
        total_nilai = alat.denda_ganti_rugi * alat.stok

        writer.writerow([
            alat.id,
            f"BRG-{alat.id:04d}",
            alat.nama_alat,
            alat.kategori.nama_kategori if alat.kategori else '-',
            alat.stok,
            alat.stok,
            alat.kondisi,
            alat.lokasi,
            alat.denda_ganti_rugi,
            total_nilai
        ])

    return response