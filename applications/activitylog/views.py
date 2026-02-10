from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from applications.activitylog.models import ActivityLog

@login_required
def dashboard(request):
    user = request.user
    context = {}

    if user.role == 'admin':
        template = "dashboard/admin.html"

        recent_logs = ActivityLog.objects.select_related('user').all()[:5]
        
        context = {
            'recent_logs': recent_logs,
            
        }

    elif user.role == 'petugas':
        template = "dashboard/petugas.html"
        
    elif user.role == 'user':
        template = "dashboard/user.html"
        context = {
            'my_logs': ActivityLog.objects.filter(user=user)[:5]
        }
        
    else:
        raise PermissionDenied

    return render(request, template, context)