from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # What shows in the user list
    list_display = (
        'username',
        'email',
        'role',
        'is_staff',
        'is_active',
        'last_login',
        'date_joined',
    )

    # Filters on the right sidebar
    list_filter = ('role', 'is_staff', 'is_active')

    # Search bar
    search_fields = ('username', 'email', 'first_name', 'last_name')

    # Default ordering
    ordering = ('-date_joined',)

    # Fields shown when opening a user
    fieldsets = UserAdmin.fieldsets + (
        ('Business Info', {
            'fields': ('role', 'deleted_at', 'updated_at'),
        }),
    )

    # Fields when creating a user
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Business Info', {
            'fields': ('role',),
        }),
    )

    # Fields that cannot be edited
    readonly_fields = (
        'last_login',
        'date_joined',
        'updated_at',
        'deleted_at',
    )
