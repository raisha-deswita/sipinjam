from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from applications.activitylog.utils import log_activity

@receiver(user_logged_in)
def catat_login(sender, request, user, **kwargs):
    log_activity(user, "User berhasil Login")

@receiver(user_logged_out)
def catat_logout(sender, request, user, **kwargs):
    log_activity(user, "User melakukan Logout")