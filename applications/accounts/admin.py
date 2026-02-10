from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'username',
        'email',
        'role',
        'is_staff',
        'is_active',
        'last_login',
        'date_joined',
    )

    list_filter = ('role', 'is_staff', 'is_active')

    search_fields = ('username', 'email', 'first_name', 'last_name')

    ordering = ('-date_joined',)

    fieldsets = UserAdmin.fieldsets + (
        ('Business Info', {
            'fields': ('role', 'deleted_at', 'updated_at'),
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Business Info', {
            'fields': ('role',),
        }),
    )

    readonly_fields = (
        'last_login',
        'date_joined',
        'updated_at',
        'deleted_at',
    )
