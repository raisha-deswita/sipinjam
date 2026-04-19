from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Count, Sum

from applications.activitylog.models import ActivityLog
from applications.accounts.decorators import role_required
from applications.activitylog.utils import log_activity
from .models import Peminjaman, Pengembalian
from .forms import PeminjamanForm, PengembalianForm
from applications.inventory.models import Alat
from applications.accounts.models import CustomUser

import csv
from django.http import HttpResponse
from django.db.models import Q

# list peminjaman/read
@login_required
def list_peminjaman(request):
    query = request.GET.get('q')
    status_filter = request.GET.get('status')
    
    # Base queryset: Admin/Petugas see all, Users see only theirs
    if request.user.role in ['admin', 'petugas']:
        peminjaman = Peminjaman.objects.all().order_by('-waktu_pinjam')
    else:
        peminjaman = Peminjaman.objects.filter(user=request.user).order_by('-waktu_pinjam')

    # Apply Search
    if query:
        peminjaman = peminjaman.filter(
            Q(user__username__icontains=query) | 
            Q(alat__nama_alat__icontains=query)
        )

    # Apply Status Filter
    now = timezone.now()
    if status_filter == 'terlambat':
        peminjaman = peminjaman.filter(status='dipinjam', waktu_kembali_rencana__lt=now)
    elif status_filter:
        peminjaman = peminjaman.filter(status=status_filter)

    context = {
        'peminjaman_list': peminjaman,
        'current_status': status_filter,
        'now': now,
    }
    return render(request, 'borrowing/list.html', context)

@login_required
def add_peminjaman(request):
    if request.method == 'POST':
        # Pass the user to the form
        form = PeminjamanForm(request.POST, user=request.user)
        if form.is_valid():
            with transaction.atomic():
                peminjaman = form.save(commit=False)
                peminjaman.user = request.user

                # Set status based on role
                if request.user.role in ['admin', 'petugas']:
                    peminjaman.status = 'dipinjam'
                else:
                    peminjaman.status = 'pending'

                peminjaman.save()

                # Update Stock
                alat = peminjaman.alat
                alat.stok -= peminjaman.jumlah
                alat.save()

                log_activity(request.user, f"Peminjaman: {alat.nama_alat} ({peminjaman.jumlah})")
                messages.success(request, "Berhasil diajukan!")
                return redirect('borrowing:list')
    else:
        form = PeminjamanForm(user=request.user)

    return render(request, 'borrowing/form_pinjam.html', {'form': form, 'title': 'Pinjam Alat'})

# approve -> ubah status pending
@login_required
@role_required(['admin', 'petugas'])
def approve_peminjaman(request, pk):
    peminjaman = get_object_or_404(Peminjaman, pk=pk)
    
    if peminjaman.status == 'pending':
        with transaction.atomic(): # Use atomic for safety
            peminjaman.status = 'dipinjam'
            peminjaman.petugas = request.user # Record who approved it
            peminjaman.save()
            
            log_activity(request.user, f"Menyetujui peminjaman: {peminjaman.alat.nama_alat} oleh {peminjaman.user.username}")
            messages.success(request, "Peminjaman disetujui! Barang siap diambil.")
    else:
        messages.error(request, "Hanya pengajuan 'Pending' yang bisa disetujui.")
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

    # --- 1. CALCULATE FIRST (Available for both POST and GET) ---
    today = timezone.now().date()
    due_date = peminjaman.waktu_kembali_rencana.date()
    selisih_hari = max(0, (today - due_date).days)
    denda_telat = selisih_hari * peminjaman.denda_per_hari

    if request.method == 'POST':
        form = PengembalianForm(request.POST, peminjaman_id=pk)
        if form.is_valid():
            with transaction.atomic():
                pengembalian = form.save(commit=False)
                pengembalian.peminjaman = peminjaman
                pengembalian.petugas = request.user
                
                # Use the calculations from above
                kondisi = form.cleaned_data['kondisi_akhir']
                # Note: We get biaya_kerusakan from POST because it's handled via partials
                input_biaya_perbaikan = int(request.POST.get('biaya_kerusakan', 0))
                
                denda_fisik = 0
                if kondisi == 'hilang':
                    denda_fisik = peminjaman.alat.denda_ganti_rugi
                elif kondisi == 'rusak':
                    denda_fisik = input_biaya_perbaikan  
                else:
                    denda_fisik = 0
                
                total_bayar = denda_telat + denda_fisik
                
                # Saving to Pengembalian model
                pengembalian.terlambat = selisih_hari
                pengembalian.biaya_kerusakan = denda_fisik 
                pengembalian.total_denda = total_bayar
                pengembalian.save()

                # Update Alat and Peminjaman status
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
        # Pass the ID for HTMX to work on initial load
        form = PengembalianForm(peminjaman_id=pk)

    # --- 2. CONTEXT (Variables are now guaranteed to exist) ---
    context = {
        'form': form,
        'peminjaman': peminjaman,
        'denda_telat': denda_telat,    
        'terlambat': selisih_hari,
        'title': 'Proses Pengembalian'
    }
    return render(request, 'borrowing/form_kembali.html', context)

def check_kondisi_view(request):
    kondisi = request.GET.get('kondisi_akhir')
    peminjaman_id = request.GET.get('peminjaman_id')
    
    # Safety check: if it's the string "None" or empty, don't crash
    if not peminjaman_id or peminjaman_id == 'None':
         return HttpResponse("Error: ID Peminjaman tidak terbaca.")

    peminjaman = get_object_or_404(Peminjaman, id=peminjaman_id)

    denda_telat = peminjaman.hitung_denda_telat
    denda_fisik = 0
    if kondisi == 'hilang':
        denda_fisik = peminjaman.alat.denda_ganti_rugi
    
    total_tagihan = denda_telat + denda_fisik

    context = {
        'kondisi': kondisi,
        'peminjaman': peminjaman,
        'total_tagihan': total_tagihan, # To update #live-total
        'denda_fisik': denda_fisik      # To update #live-fisik
    }
    return render(request, 'borrowing/partials/biaya_detail.html', context)
    
def update_receipt_view(request):
    try:
        biaya_tambahan = int(request.GET.get('biaya_kerusakan', 0))
    except ValueError:
        biaya_tambahan = 0
        
    peminjaman_id = request.GET.get('peminjaman_id')
    peminjaman = get_object_or_404(Peminjaman, id=peminjaman_id)
    
    total = peminjaman.hitung_denda_telat + biaya_tambahan
    
    # Return just the number for the total
    return HttpResponse(f"Rp {total:,}")

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