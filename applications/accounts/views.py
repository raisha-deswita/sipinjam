from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.contrib.auth import get_user_model

from applications.activitylog.models import ActivityLog
from applications.inventory.models import Alat
from applications.borrowings.models import Peminjaman
from applications.activitylog.utils import log_activity

from .forms import RegisterForm
from .decorators import role_required

User = get_user_model()

@login_required
def dashboard(request):
    user = request.user
    context = {}

    if user.role == 'admin':
        template = "dashboard/admin.html"
        context['total_users'] = User.objects.count()
        context['total_alat'] = Alat.objects.count()
        context['recent_logs'] = ActivityLog.objects.select_related('user').order_by('-timestamp')[:10]

    elif user.role == 'petugas':
        template = "dashboard/petugas.html"
        context['pending_count'] = Peminjaman.objects.filter(status='pending').count()
        context['dipinjam_count'] = Peminjaman.objects.filter(status='dipinjam').count()
        
    elif user.role == 'user':
        template = "dashboard/user.html"
        context['my_loans'] = Peminjaman.objects.filter(user=user, status='dipinjam')
        context['my_pending'] = Peminjaman.objects.filter(user=user, status='pending').count()

    else:
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