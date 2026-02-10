from .models import ActivityLog

def log_activity(user, action_text):
    """
    Utility function to log user activities
    """
    if user.is_authenticated:
        ActivityLog.objects.create(
            user=user,
            action=action_text
        )