from django.db import models
from django.conf import settings

class ActivityLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='logs'
    )

    action = models.CharField(max_length=255) 
    timestamp = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Activity Log"
        verbose_name_plural = "Activity Logs"

    def __str__(self):
        return f"{self.user.username} - {self.action} ({self.timestamp.strftime('%Y-%m-%d %H:%M')})"

    def soft_delete(self):
        self.is_deleted = True
        self.save()
