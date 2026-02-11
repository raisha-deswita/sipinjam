from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from datetime import datetime, timedelta
from django.utils import timezone

from applications.accounts.decorators import role_required
from applications.activitylog.utils import log_activity
from .models import Peminjaman, Pengembalian
from .forms import PeminjamanForm, PengembalianForm
from applications.inventory.models import Alat

import csv
from django.http import HttpResponse
from django.db.models import Q

# list peminjaman/read
@login_required
def list_peminjaman(request):
    # Admin/Petugas --> Bisa lihat semua data
    # User Biasa --> Cuma bisa lihat data dirinya sendiri
    if request.user.role in ['admin', 'petugas']:
        peminjaman_list = Peminjaman.objects.select_related('user', 'alat').all()
    else:
        peminjaman_list = Peminjaman.objects.filter(user=request.user).select_related('alat')

    context = {
        'peminjaman_list': peminjaman_list,
        'title': 'Daftar Peminjaman'
    }
    return render(request, 'borrowing/list.html', context)

# Tambah Peminjaman/create -> stok berkurang
@login_required
def add_peminjaman(request):
    if request.method == 'POST':
        form = PeminjamanForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                peminjaman = form.save(commit=False)
                peminjaman.user = request.user

                if request.user.role in ['admin', 'petugas']:
                    peminjaman.status = 'dipinjam'
                    msg = "Peminjaman berhasil dicatat."
                else:
                    peminjaman.status = 'pending'
                    msg = "Pengajuan berhasil! Tunggu persetujuan petugas ya."
                peminjaman.save()

                alat = peminjaman.alat
                alat.stok -= peminjaman.jumlah
                alat.save()

                log_activity(request.user, f"Mengajukan peminjaman: {alat.nama_alat} ({peminjaman.jumlah} unit)")
                
                messages.success(request, msg)
                return redirect('borrowing:list')
    else:
        form = PeminjamanForm()

    return render(request, 'borrowing/form_pinjam.html', {'form': form, 'title': 'Pinjam Alat'})

# approve -> ubah status pending
@login_required
@role_required(['admin', 'petugas'])
def approve_peminjaman(request, pk):
    peminjaman = get_object_or_404(Peminjaman, pk=pk)
    
    if peminjaman.status == 'pending':
        peminjaman.status = 'dipinjam'
        peminjaman.save()
        
        log_activity(request.user, f"Menyetujui peminjaman: {peminjaman.alat.nama_alat} oleh {peminjaman.user.username}")
        messages.success(request, "Peminjaman disetujui! Barang siap diambil.")
    
    return redirect('borrowing:list')

# reject -> balikin stok, tandai batal
@login_required
@role_required(['admin', 'petugas'])
def reject_peminjaman(request, pk):
    peminjaman = get_object_or_404(Peminjaman, pk=pk)
    
    if peminjaman.status == 'pending':
        with transaction.atomic():
            alat = peminjaman.alat
            alat.stok += peminjaman.jumlah
            alat.save()

            peminjaman.status = 'ditolak'
            peminjaman.save()
            
            log_activity(request.user, f"Menolak peminjaman: {alat.nama_alat} oleh {peminjaman.user.username}")
            
            messages.info(request, "Pengajuan ditolak. Stok barang telah dikembalikan ke gudang.")
    
    return redirect('borrowing:list')

# pengembalian alat/update -> stok bertambah (kecuali barang hilang)
@login_required
@role_required(['admin', 'petugas'])
def kembalikan_alat(request, pk):
    peminjaman = get_object_or_404(Peminjaman, pk=pk)

    if peminjaman.status == 'dikembalikan':
        messages.warning(request, "Transaksi ini sudah selesai sebelumnya.")
        return redirect('borrowing:list')

    if request.method == 'POST':
        form = PengembalianForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                pengembalian = form.save(commit=False)
                pengembalian.peminjaman = peminjaman
                pengembalian.petugas = request.user
               
                tanggal_janji = peminjaman.waktu_kembali_rencana.date()
                tanggal_sekarang = timezone.now().date()
                selisih_hari = (tanggal_sekarang - tanggal_janji).days
                terlambat = max(0, selisih_hari)
                denda_telat = terlambat * peminjaman.denda_per_hari

                kondisi = form.cleaned_data['kondisi_akhir']
                input_biaya_perbaikan = form.cleaned_data['biaya_kerusakan']
                
                denda_fisik = 0

                if kondisi == 'hilang':
                    denda_fisik = peminjaman.alat.denda_ganti_rugi
                elif kondisi == 'rusak':
                    denda_fisik = input_biaya_perbaikan  
                else:
                    denda_fisik = 0
                
                total_bayar = denda_telat + denda_fisik
                pengembalian.terlambat = terlambat
                pengembalian.biaya_kerusakan = denda_fisik 
                pengembalian.total_denda = denda_telat + denda_fisik 
                pengembalian.save()

                alat = peminjaman.alat
                
                if kondisi == 'hilang':
                    peminjaman.status = 'hilang'
                
                elif kondisi == 'rusak':
                    peminjaman.status = 'dikembalikan'
                    alat.stok += peminjaman.jumlah
                    alat.kondisi = 'rusak'
                
                else:
                    peminjaman.status = 'dikembalikan'
                    alat.stok += peminjaman.jumlah

                alat.save()
                peminjaman.save()

                log_activity(request.user, f"Menerima pengembalian: {alat.nama_alat}. Denda: Rp {total_bayar}")
                messages.success(request, f"Barang diterima. Total Denda: Rp {total_bayar}")
                
                return redirect('borrowing:list')
    else:
        form = PengembalianForm()

    context = {
        'form': form,
        'peminjaman': peminjaman,
        'denda_estimasi': 0,
        'title': 'Proses Pengembalian'
    }
    return render(request, 'borrowing/form_kembali.html', context)

# download laporan csv
@login_required
@role_required(['admin', 'petugas'])
def download_laporan(request):
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="laporan_{timezone.now().date()}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Peminjam', 'Alat', 'Jumlah', 
        'Tgl Pinjam', 'Tenggat', 'Tgl Kembali', 
        'Status', 'Kondisi', 'Denda Telat', 'Biaya Kerusakan', 'Total Denda'
    ])

    queryset = Peminjaman.objects.select_related('user', 'alat').all().order_by('-waktu_pinjam')

    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")

            end_date_plus_one = end_date + timedelta(days=1)

            queryset = queryset.filter(
                waktu_pinjam__gte=start_date, 
                waktu_pinjam__lt=end_date_plus_one
            )

        except ValueError:
            pass

    for p in queryset:
        tgl_kembali = '-'
        
        waktu_pinjam_lokal = timezone.localtime(p.waktu_pinjam)
        waktu_rencana_lokal = timezone.localtime(p.waktu_kembali_rencana)
        
        str_pinjam = waktu_pinjam_lokal.strftime("%Y-%m-%d %H:%M")
        str_tenggat = waktu_rencana_lokal.strftime("%Y-%m-%d")

        kondisi = '-'
        denda_telat = 0
        biaya_rusak = 0
        total_denda = 0

        try:
            if hasattr(p, 'detail_pengembalian'):
                pengembalian = p.detail_pengembalian
                
                waktu_balik_lokal = timezone.localtime(pengembalian.waktu_kembali_realisasi)
                tgl_kembali = waktu_balik_lokal.strftime("%Y-%m-%d %H:%M")
                
                kondisi = pengembalian.kondisi_akhir
                biaya_rusak = pengembalian.biaya_kerusakan
                total_denda = pengembalian.total_denda
                denda_telat = total_denda - biaya_rusak
        except Exception:
            pass 

        writer.writerow([
            p.id,
            p.user.username,
            p.alat.nama_alat,
            p.jumlah,
            str_pinjam,   
            str_tenggat,
            tgl_kembali,  
            p.get_status_display(),
            kondisi,
            denda_telat,
            biaya_rusak,
            total_denda
        ])

    return response

@login_required
@role_required(['admin', 'petugas'])
def download_laporan_denda(request):

    response = HttpResponse(content_type='text/csv')
    filename = f"laporan_KEUANGAN_DENDA_{timezone.now().date()}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    
    writer.writerow([
        'ID Transaksi', 'Peminjam', 'Tanggal Kembali', 
        'Denda Keterlambatan', 'Biaya Kerusakan', 'TOTAL MASUK'
    ])

    queryset = Peminjaman.objects.filter(
        detail_pengembalian__total_denda__gt=0
    ).select_related('user', 'detail_pengembalian').order_by('-detail_pengembalian__waktu_kembali_realisasi')

    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            end_date_plus_one = end_date + timedelta(days=1)
            
            queryset = queryset.filter(
                detail_pengembalian__waktu_kembali_realisasi__gte=start_date,
                detail_pengembalian__waktu_kembali_realisasi__lt=end_date_plus_one
            )
        except ValueError:
            pass

    grand_total_denda = 0

    for p in queryset:
        pengembalian = p.detail_pengembalian
        
        biaya_rusak = pengembalian.biaya_kerusakan
        total_per_transaksi = pengembalian.total_denda
        denda_telat = total_per_transaksi - biaya_rusak
        
        grand_total_denda += total_per_transaksi

        waktu_balik_lokal = timezone.localtime(pengembalian.waktu_kembali_realisasi)
        tgl_kembali_str = waktu_balik_lokal.strftime("%Y-%m-%d %H:%M")

        writer.writerow([
            p.id,
            p.user.username,
            tgl_kembali_str,
            denda_telat,
            biaya_rusak,
            total_per_transaksi
        ])

    writer.writerow([])
    writer.writerow(['', '', '', '', 'TOTAL PENDAPATAN:', grand_total_denda])

    return response

# lunasi denda
@login_required
@role_required(['admin', 'petugas'])
def lunasi_denda(request, pk):
    pengembalian = get_object_or_404(Pengembalian, peminjaman__id=pk)

    if pengembalian.total_denda > 0 and pengembalian.status_pembayaran == 'belum_lunas':
        with transaction.atomic():
            pengembalian.status_pembayaran = 'lunas'
            pengembalian.save()
            
            log_activity(
                request.user, 
                f"Menerima pelunasan denda: Rp {pengembalian.total_denda} dari {pengembalian.peminjaman.user.username}"
            )
            
            messages.success(request, "LUNAS! Uang denda berhasil diterima.")
    else:
        messages.warning(request, "Tidak ada tagihan yang perlu dibayar.")
    
    return redirect('borrowing:list')