from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from .models import CustomUser

@login_required
def dashboard(request):
    user = request.user
    if user.role == CustomUser.ROLE_ADMIN:
        template = "dashboard/admin.html"
    elif user.role == CustomUser.ROLE_PETUGAS:
        template = "dashboard/petugas.html"
    elif user.role == CustomUser.ROLE_USER:
        template = "dashboard/user.html"
    else:
        raise PermissionDenied

    return render(request, template)
