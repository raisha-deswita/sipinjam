from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLE_ADMIN = 'admin'
    ROLE_PETUGAS = 'petugas'
    ROLE_USER = 'user'

    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Admin'),
        (ROLE_PETUGAS, 'Petugas'),
        (ROLE_USER, 'User'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_USER
    )

    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def is_admin(self):
        return self.role == self.ROLE_ADMIN

    def is_petugas(self):
        return self.role == self.ROLE_PETUGAS
