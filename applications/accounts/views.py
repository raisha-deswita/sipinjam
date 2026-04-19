import datetime
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models.functions import ExtractMonth
from django.db.models import Sum, Count
from django.utils import timezone

from applications.activitylog.models import ActivityLog
from applications.inventory.models import Alat
from applications.borrowings.models import Peminjaman, Pengembalian
from applications.activitylog.utils import log_activity

from .forms import RegisterForm
from .decorators import role_required

User = get_user_model()

# dynamified dashboard

@login_required
def dashboard(request):
    user = request.user
    context = {}

    if user.role == 'admin':
        template = "dashboard/admin.html"
        
        # 1. Stats Utama
        total_users = User.objects.count()
        total_alat = Alat.objects.aggregate(total=Sum('stok'))['total'] or 0
        sedang_dipinjam = Peminjaman.objects.filter(status='dipinjam').count()
        total_kas = Pengembalian.objects.filter(status_pembayaran='lunas').aggregate(total=Sum('total_denda'))['total'] or 0

        # 2. Pie Chart Data (Berdasarkan kondisi fisik barang yang dikembalikan)
        baik_count = Pengembalian.objects.filter(kondisi_akhir='baik').count()
        rusak_count = Pengembalian.objects.filter(kondisi_akhir='rusak').count()
        hilang_count = Pengembalian.objects.filter(kondisi_akhir='hilang').count()
        
        # 3. Grafik Batang (Peminjaman per Bulan di Tahun Ini)
        current_year = datetime.datetime.now().year
        monthly_stats = Peminjaman.objects.filter(
            waktu_pinjam__year=current_year, 
            waktu_pinjam__isnull=False 
        ).annotate(month=ExtractMonth('waktu_pinjam'))\
        .values('month')\
        .annotate(count=Count('id'))\
        .order_by('month')

        data_peminjaman = [0] * 12
        for stat in monthly_stats:
            if stat['month'] is not None:  # <--- Cek dulu bulannya ada nggak
                data_peminjaman[stat['month']-1] = stat['count']

        # 4. Masukkan semua ke context
        context = {
            'total_users': total_users,
            'total_alat': total_alat,
            'sedang_dipinjam': sedang_dipinjam,
            'total_kas': total_kas,
            'baik_count': baik_count,
            'rusak_count': rusak_count,
            'hilang_count': hilang_count,
            'data_peminjaman': data_peminjaman,
            'recent_logs': ActivityLog.objects.select_related('user').all().order_by('-timestamp')[:10],
        }

    elif user.role == 'petugas':
        template = "dashboard/petugas.html"
        now = timezone.now()
        
        # Stats khusus petugas
        pending_count = Peminjaman.objects.filter(status='pending').count()
        dipinjam_count = Peminjaman.objects.filter(status='dipinjam').count()
        terlambat_count = Peminjaman.objects.filter(status='dipinjam', waktu_kembali_rencana__lt=now).count()
        
        # Ambil 5 permintaan terbaru yang butuh perhatian (Pending atau Dipinjam)
        recent_requests = Peminjaman.objects.filter(
            status__in=['pending', 'dipinjam']
        ).select_related('user', 'alat').order_by('-waktu_pinjam')[:5]
        
        context = {
            'pending_count': pending_count,
            'dipinjam_count': dipinjam_count,
            'terlambat_count': terlambat_count,
            'recent_requests': recent_requests,
            'now': now,
        }
    
    elif user.role == 'user':
        template = "dashboard/user.html"
        
        # 1. Barang yang sedang dibawa (Status: Dipinjam)
        my_loans = Peminjaman.objects.filter(user=user, status='dipinjam').select_related('alat')
        
        # 2. Hitung jumlah request yang masih pending
        my_pending = Peminjaman.objects.filter(user=user, status='pending').count()
        
        # 3. Hitung TOTAL denda yang BELUM LUNAS (Hutang Siswa)
        # Kita ambil dari tabel Pengembalian yang status_pembayarannya 'belum_lunas'
        my_debt = Pengembalian.objects.filter(
            peminjaman__user=user, 
            status_pembayaran='belum_lunas'
        ).aggregate(total=Sum('total_denda'))['total'] or 0

        context = {
            'my_loans': my_loans,
            'my_loans_count': my_loans.count(),
            'my_pending': my_pending,
            'my_debt': my_debt,
            'now': timezone.now(),
        }
    
    else:
        # Jika role tidak dikenal
        raise PermissionDenied

    return render(request, template, context)

def register_siswa(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'user'
            user.save()
            
            messages.success(request, "Registrasi berhasil! Silakan login.")
            return redirect('login')
    else:
        form = RegisterForm()

    return render(request, 'registration/register.html', {'form': form})

@login_required
@role_required(['admin'])
def add_petugas(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'petugas'
            user.is_staff = True
            user.save()
            
            log_activity(request.user, f"Menambahkan petugas baru: {user.username}")
            
            messages.success(request, f"Petugas {user.username} berhasil ditambahkan!")
            return redirect('dashboard')
    else:
        form = RegisterForm()

    return render(request, 'registration/add_petugas.html', {'form': form})